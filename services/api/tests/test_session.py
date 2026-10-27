import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app

client = TestClient(app)


def new_sid() -> str:
    res = client.post("/api/session")
    assert res.status_code == 200
    body = res.json()
    assert body["phone_path"] == f"/m?sid={body['session_id']}"
    return body["session_id"]


def test_session_ids_are_unique():
    assert new_sid() != new_sid()


def test_unknown_session_is_closed_with_4404():
    with client.websocket_connect("/api/ws/phone/nope") as ws:
        with pytest.raises(WebSocketDisconnect) as e:
            ws.receive_json()
        assert e.value.code == 4404


def test_phone_frames_reach_dashboard_and_latest_jpg():
    sid = new_sid()
    assert client.get(f"/api/session/{sid}/latest.jpg").status_code == 404

    with client.websocket_connect(f"/api/ws/dash/{sid}") as dash:
        assert dash.receive_json() == {"type": "status", "phone_connected": False, "frames": 0}

        with client.websocket_connect(f"/api/ws/phone/{sid}") as phone:
            assert phone.receive_json() == {"type": "ready"}
            assert dash.receive_json()["phone_connected"] is True

            phone.send_bytes(b"\xff\xd8fake-jpeg\xff\xd9")
            assert dash.receive_json() == {"type": "status", "phone_connected": True, "frames": 1}

        # 폰이 끊기면 대시보드에 알려 준다
        assert dash.receive_json()["phone_connected"] is False

    res = client.get(f"/api/session/{sid}/latest.jpg")
    assert res.status_code == 200
    assert res.content == b"\xff\xd8fake-jpeg\xff\xd9"


def test_second_phone_replaces_first():
    sid = new_sid()
    with client.websocket_connect(f"/api/ws/phone/{sid}") as first:
        assert first.receive_json() == {"type": "ready"}
        with client.websocket_connect(f"/api/ws/phone/{sid}") as second:
            assert second.receive_json() == {"type": "ready"}
            with pytest.raises(WebSocketDisconnect) as e:
                first.receive_json()
            assert e.value.code == 4409
