"""대시보드 ② 실시간 저장 현황.

- ocr_worker: frame_queue 에서 프레임을 꺼내 pipeline 에 보내고, 새로 저장된 문장을 대시보드에 푸시한다.
- GET /api/stored     처음 화면을 열 때 최근 저장 목록 + 전체 개수
- GET /api/passages   카드 제목으로 묶은 지문 목록 (기획의 "11 / 100 저장"은 지문 수)
- GET /api/pipeline   pipeline 상태 (모델 로드 중인지, 꺼졌는지, 저장소 종류) → 대시보드 안내 문구용
- WS  /api/ws/stored  새로 저장될 때마다 {"type":"stored","items":[...],"total":n}

저장 현황은 QR 세션과 상관없이 DB 전체 기준이라 세션 없이 접속한다.
"""
import asyncio
import logging

import httpx
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from .frames import frame_queue
from .pipeline_client import pipeline

log = logging.getLogger("uvicorn.error")
router = APIRouter()
watchers: set[WebSocket] = set()


async def broadcast(message: dict) -> None:
    for ws in list(watchers):
        try:
            await ws.send_json(message)
        except Exception:
            watchers.discard(ws)


def _item(row: dict) -> dict:
    return {"id": row["id"], "text": row["text"], "meta": row.get("meta", {})}


async def ocr_worker() -> None:
    frame_no = 0
    while True:
        frame = await frame_queue.get()
        frame_no += 1
        try:
            res = await pipeline.post(
                "/process",
                params={"session": frame.sid, "frame_no": frame_no},
                content=frame.image,
                headers={"Content-Type": "image/jpeg"},
            )
            if res.status_code == 503:  # pipeline 이 아직 모델을 불러오는 중 → 이 프레임은 버린다
                continue
            res.raise_for_status()
            result = res.json()
        except httpx.HTTPError as e:
            log.warning("pipeline 호출 실패: %s", e)
            await asyncio.sleep(2)  # pipeline 이 꺼져 있을 때 로그가 폭주하지 않게
            continue

        if result["stored"]:
            await broadcast({
                "type": "stored",
                "items": [_item(s) for s in result["stored"]],
                "total": result["total"],
            })


async def _get_from_pipeline(path: str, **params) -> dict:
    try:
        res = await pipeline.get(path, params=params)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail="pipeline 서비스에 연결할 수 없습니다") from e
    if res.status_code != 200:
        raise HTTPException(status_code=503, detail=res.json().get("detail", "pipeline 준비 중"))
    return res.json()


@router.get("/api/stored")
async def stored(limit: int = 30):
    body = await _get_from_pipeline("/recent", limit=limit)
    return {"items": [_item(r) for r in body["items"]], "total": body["total"]}


@router.get("/api/passages")
async def passages():
    return await _get_from_pipeline("/passages")


@router.get("/api/pipeline")
async def pipeline_status():
    """pipeline 이 꺼져 있어도 에러 대신 reachable=false 로 답한다 (대시보드가 상태를 보여 줄 수 있게)."""
    try:
        res = await pipeline.get("/health", timeout=5)
        res.raise_for_status()
    except httpx.HTTPError:
        return {"reachable": False, "ready": False, "load_error": None, "store": None}
    return {"reachable": True, **res.json()}


@router.websocket("/api/ws/stored")
async def stored_ws(ws: WebSocket):
    await ws.accept()
    watchers.add(ws)
    try:
        while True:
            await ws.receive_text()  # 받는 건 없다. 연결 유지 + 끊김 감지용
    except WebSocketDisconnect:
        pass
    finally:
        watchers.discard(ws)
