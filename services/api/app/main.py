"""api 서비스: QR 세션 발급 + 폰 프레임 수신(WebSocket) + 대시보드 상태 푸시.

엔드포인트 (모두 /api 아래)
  POST /api/session                    세션 발급 → {session_id, phone_path, expires_in}
  WS   /api/ws/phone/{sid}             폰 → 서버: JPEG 프레임(바이너리)
  WS   /api/ws/dash/{sid}              서버 → 대시보드: {"type":"status", phone_connected, frames}
  GET  /api/session/{sid}/latest.jpg   가장 최근 프레임 (카메라 방향 확인용)
  저장 현황(GET /api/stored, WS /api/ws/stored)은 storage.py, RAG(POST /api/rag)는 rag.py
"""
import asyncio
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import rag, storage
from .frames import frame_queue
from .sessions import SESSION_TTL_SECONDS, store

MAX_FRAME_BYTES = 2 * 1024 * 1024  # 프레임 하나 최대 2MB
STATUS_INTERVAL = 1.0  # 프레임이 계속 들어올 때 대시보드에 상태를 보내는 최소 간격(초)

# 폰 close 코드
CLOSE_NO_SESSION = 4404  # 없는/만료된 세션
CLOSE_REPLACED = 4409  # 같은 세션에 다른 폰이 붙어서 밀려남
CLOSE_EXPIRED = 4410  # 연결 중 세션 만료

@asynccontextmanager
async def lifespan(app: FastAPI):
    # frame_queue 의 프레임을 pipeline 으로 보내는 일꾼 (OCR_WORKER=0 이면 끔: 테스트용)
    worker = asyncio.create_task(storage.ocr_worker()) if os.getenv("OCR_WORKER", "1") == "1" else None
    yield
    if worker:
        worker.cancel()


app = FastAPI(title="ocr-rag api", lifespan=lifespan)
app.include_router(storage.router)
app.include_router(rag.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/session")
def create_session():
    session = store.create()
    return {
        "session_id": session.sid,
        "phone_path": f"/m?sid={session.sid}",
        "expires_in": SESSION_TTL_SECONDS,
    }


@app.get("/api/session/{sid}/latest.jpg")
def latest_frame(sid: str):
    session = store.get(sid)
    if session is None or session.latest is None:
        raise HTTPException(status_code=404)
    return Response(content=session.latest, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@app.websocket("/api/ws/phone/{sid}")
async def phone_ws(ws: WebSocket, sid: str):
    await ws.accept()
    session = store.get(sid)
    if session is None:
        await ws.close(code=CLOSE_NO_SESSION)
        return

    # 같은 세션에 폰이 이미 붙어 있으면 새 폰으로 교체한다 (두 폰의 프레임이 섞이지 않게)
    if session.phone is not None:
        old = session.phone
        session.phone = None
        try:
            await old.close(code=CLOSE_REPLACED)
        except Exception:
            pass
    session.phone = ws
    await ws.send_json({"type": "ready"})
    await session.broadcast()

    try:
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                break
            data = message.get("bytes")
            if data is None:
                continue  # 텍스트 메시지는 지금은 쓰지 않는다
            if len(data) > MAX_FRAME_BYTES:
                await ws.close(code=1009)  # Message Too Big
                break
            if session.expired:
                await ws.send_json({"type": "stop"})
                await ws.close(code=CLOSE_EXPIRED)
                break

            session.frames += 1
            session.latest = data
            frame_queue.put_latest(sid, data)

            now = time.monotonic()
            if now - session.last_push >= STATUS_INTERVAL:
                session.last_push = now
                await session.broadcast()
    except WebSocketDisconnect:
        pass
    finally:
        if session.phone is ws:  # 밀려난 폰이 아닐 때만 '끊김'으로 처리
            session.phone = None
            await session.broadcast()


@app.websocket("/api/ws/dash/{sid}")
async def dash_ws(ws: WebSocket, sid: str):
    await ws.accept()
    session = store.get(sid)
    if session is None:
        await ws.close(code=CLOSE_NO_SESSION)
        return

    session.dashboards.add(ws)
    try:
        await ws.send_json(session.status())
        while True:
            await ws.receive_text()  # 대시보드는 보내는 게 없다. 연결 유지 + 끊김 감지용
    except WebSocketDisconnect:
        pass
    finally:
        session.dashboards.discard(ws)


# ---- 빌드된 프론트엔드 서빙 (폰 테스트용) -------------------------------------------------
# `npm run build` 로 만든 build/ 폴더가 있으면 같은 서버(같은 주소)에서 함께 서빙한다.
# 그러면 터널(https)을 하나만 열어도 QR 페이지, 폰 촬영 페이지, API, WebSocket 이 모두 한 주소로 동작한다.
# 다른 위치를 쓰려면 환경변수 FRONTEND_DIR 를 지정한다.
def _frontend_dir() -> Path | None:
    env = os.getenv("FRONTEND_DIR")
    if env:
        path = Path(env)
    else:
        parents = Path(__file__).resolve().parents
        if len(parents) < 4:  # Docker 안처럼 레포 구조가 아니면 서빙하지 않는다
            return None
        path = parents[3] / "build"
    return path if (path / "index.html").is_file() else None


FRONTEND_DIR = _frontend_dir()

if FRONTEND_DIR is not None:
    root = FRONTEND_DIR.resolve()
    app.mount("/static", StaticFiles(directory=root / "static"), name="static")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        target = (root / path).resolve()
        if path and target.is_file() and root in target.parents:
            return FileResponse(target)
        return FileResponse(root / "index.html")  # /m, /pair 같은 화면 주소
