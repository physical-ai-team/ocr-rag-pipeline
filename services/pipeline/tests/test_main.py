import io
import os

os.environ["FAKE_MODELS"] = "1"  # 무거운 모델 대신 가짜 OCR/임베딩
os.environ["SUPABASE_URL"] = ""  # 메모리 저장소 사용

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import main


def jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 20), "white").save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture()
def client():
    with TestClient(main.app) as c:
        while not main.pipe.ready:  # 가짜 모델이라 바로 끝난다
            pass
        yield c


def fake_ocr(monkeypatch, text):
    monkeypatch.setattr(main.pipe.ocr, "read_columns", lambda img: [[(text, 0.99)]])


def test_health(client):
    body = client.get("/health").json()
    assert body["ready"] is True
    assert body["store"] == "MemoryStore"


def test_process_stores_sentences_and_skips_duplicates(client, monkeypatch):
    fake_ocr(monkeypatch, "The kettle must be filled before boiling. Never leave it switched on when empty.")

    first = client.post("/process", params={"session": "s1", "frame_no": 1}, content=jpeg()).json()
    assert [s["text"] for s in first["stored"]] == [
        "The kettle must be filled before boiling.",
        "Never leave it switched on when empty.",
    ]
    assert first["total"] == 2

    # 같은 화면을 다시 찍으면 저장하지 않는다
    second = client.post("/process", params={"session": "s1", "frame_no": 2}, content=jpeg()).json()
    assert second["stored"] == []
    assert second["duplicates"] == 2
    assert second["total"] == 2


def test_search_and_recent(client, monkeypatch):
    fake_ocr(monkeypatch, "Migratory birds fly south in autumn. Paper was invented in ancient China.")
    client.post("/process", params={"session": "s2"}, content=jpeg())

    results = client.post("/search", json={"query": "Where was paper invented?", "k": 1}).json()["results"]
    assert results[0]["text"] == "Paper was invented in ancient China."

    recent = client.get("/recent", params={"limit": 1}).json()
    assert len(recent["items"]) == 1
    assert recent["total"] >= 2


def test_passages_endpoint(client, monkeypatch):
    monkeypatch.setattr(main.pipe.ocr, "read_columns", lambda img: [[
        ("ON Losing Things", 0.99), ("Keys are never lost in interesting places. They are found in the coat.", 0.99)]])
    client.post("/process", params={"session": "s3"}, content=jpeg())
    body = client.get("/passages").json()
    assert [(p["title"], p["sentences"]) for p in body["passages"]] == [("On Losing Things", 2)]


def test_empty_body_is_rejected(client):
    assert client.post("/process", params={"session": "s"}, content=b"").status_code == 400
