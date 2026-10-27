import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import rag, storage
from app.main import app

STORED = [{"id": "a1", "text": "Paper was invented in ancient China.", "meta": {"session": "s"}}]


def fake_pipeline(request: httpx.Request) -> httpx.Response:
    """pipeline 서비스 흉내."""
    if request.url.path == "/process":
        return httpx.Response(200, json={"stored": STORED, "duplicates": 0, "total": 7})
    if request.url.path == "/recent":
        return httpx.Response(200, json={"items": STORED, "total": 7})
    if request.url.path == "/search":
        assert json.loads(request.content)["query"] == "Where was paper invented?"
        return httpx.Response(200, json={"results": [{**STORED[0], "score": 0.81}]})
    return httpx.Response(404)


@pytest.fixture(autouse=True)
def mock_pipeline(monkeypatch):
    client = httpx.AsyncClient(base_url="http://pipeline", transport=httpx.MockTransport(fake_pipeline))
    monkeypatch.setattr(storage, "pipeline", client)
    monkeypatch.setattr(rag, "pipeline", client)


def test_stored_list():
    body = TestClient(app).get("/api/stored").json()
    assert body == {"items": STORED, "total": 7}


def test_frame_is_processed_and_pushed_to_storage_watchers():
    with TestClient(app) as client:  # with: lifespan 이 돌아서 ocr_worker 가 켜진다
        sid = client.post("/api/session").json()["session_id"]
        with client.websocket_connect("/api/ws/stored") as watcher:
            with client.websocket_connect(f"/api/ws/phone/{sid}") as phone:
                phone.receive_json()  # ready
                phone.send_bytes(b"\xff\xd8fake-jpeg\xff\xd9")
                assert watcher.receive_json() == {"type": "stored", "items": STORED, "total": 7}


def test_rag_without_key_returns_sources_only(monkeypatch):
    monkeypatch.setattr(rag, "GEMINI_API_KEY", "")
    body = TestClient(app).post("/api/rag", json={"question": "Where was paper invented?"}).json()
    assert body["answer"] is None
    assert body["sources"] == [{"n": 1, "id": "a1", "text": STORED[0]["text"], "score": 0.81}]


def test_rag_with_gemini(monkeypatch):
    seen = {}

    class FakeModels:
        async def generate_content(self, model, contents, config):
            seen["contents"] = contents
            return type("Reply", (), {"text": "중국에서 발명되었습니다 [1]."})()

    fake = type("Client", (), {"aio": type("Aio", (), {"models": FakeModels()})()})()
    monkeypatch.setattr(rag, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(rag, "gemini", lambda: fake)

    body = TestClient(app).post("/api/rag", json={"question": "Where was paper invented?"}).json()
    assert body["answer"] == "중국에서 발명되었습니다 [1]."
    assert "[1] Paper was invented in ancient China." in seen["contents"]


def fake_gemini(monkeypatch, behaviour):
    """behaviour: {모델 이름: 답 문자열 또는 던질 예외}"""
    class FakeModels:
        async def generate_content(self, model, contents, config):
            out = behaviour[model]
            if isinstance(out, Exception):
                raise out
            return type("Reply", (), {"text": out})()

    fake = type("Client", (), {"aio": type("Aio", (), {"models": FakeModels()})()})()
    monkeypatch.setattr(rag, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(rag, "GEMINI_MODEL", "main-model")
    monkeypatch.setattr(rag, "GEMINI_FALLBACK_MODEL", "backup-model")
    monkeypatch.setattr(rag, "gemini", lambda: fake)


def test_rag_falls_back_when_main_model_is_busy(monkeypatch):
    fake_gemini(monkeypatch, {"main-model": RuntimeError("503 UNAVAILABLE"), "backup-model": "중국 [1]."})
    body = TestClient(app).post("/api/rag", json={"question": "Where was paper invented?"}).json()
    assert body["answer"] == "중국 [1]."
    assert body["model"] == "backup-model"
    assert body["error"] is None


def test_rag_returns_sources_when_all_models_fail(monkeypatch):
    fake_gemini(monkeypatch, {"main-model": RuntimeError("503"), "backup-model": RuntimeError("429 quota")})
    res = TestClient(app).post("/api/rag", json={"question": "Where was paper invented?"})
    assert res.status_code == 200  # 화면이 멈추거나 에러로 끝나지 않고 근거 문장은 보여 준다
    body = res.json()
    assert body["answer"] is None
    assert len(body["sources"]) == 1
    assert "429 quota" in body["error"]


def test_pipeline_down_gives_503(monkeypatch):
    def down(request):
        raise httpx.ConnectError("down")

    client = httpx.AsyncClient(base_url="http://pipeline", transport=httpx.MockTransport(down))
    monkeypatch.setattr(storage, "pipeline", client)
    assert TestClient(app).get("/api/stored").status_code == 503
