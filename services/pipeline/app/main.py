"""pipeline 서비스: pipeline.py(OCR → 임베딩 → 저장)를 HTTP 로 감싼 서버. api 서비스만 이 서버를 부른다.

엔드포인트
  GET  /health                         모델 로드 상태, 저장소 종류, 저장된 문장 수
  POST /process?session=..&frame_no=.. 본문: JPEG 바이트 → OCR·임베딩·저장 결과 + total
  POST /search                         {"query": "...", "k": 5} → 질문과 가까운 문장 top-k (RAG 용)
  GET  /recent?limit=30                최근 저장된 문장 + total
"""
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from .pipeline import Pipeline

pipe: Pipeline | None = None
# OCR/임베딩 모델과 중복 검사용 _seen 은 동시에 쓰면 안 되므로 한 번에 한 요청만 처리한다
lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipe
    pipe = Pipeline()
    # 모델 로드는 처음에 몇 분 걸릴 수 있다. 그동안에도 /health 는 응답하도록 따로 돌린다
    threading.Thread(target=pipe.load, daemon=True).start()
    yield


app = FastAPI(title="ocr-rag pipeline", lifespan=lifespan)


def ready_pipe() -> Pipeline:
    if pipe is None or not pipe.ready:
        detail = pipe.load_error if pipe and pipe.load_error else "모델을 불러오는 중"
        raise HTTPException(status_code=503, detail=detail)
    return pipe


@app.get("/health")
def health():
    return {
        "ready": bool(pipe and pipe.ready),
        "load_error": pipe.load_error if pipe else None,
        "store": type(pipe.store).__name__ if pipe else None,
        "total": pipe.store.count() if pipe else 0,
    }


@app.post("/process")
async def process(request: Request, session: str, frame_no: int = 0):
    p = ready_pipe()
    jpeg = await request.body()
    if not jpeg:
        raise HTTPException(status_code=400, detail="빈 이미지")

    def run():
        with lock:
            result = p.process_frame(jpeg, session=session, frame_no=frame_no)
            result["total"] = p.store.count()
            return result

    try:
        return await run_in_threadpool(run)
    except OSError as e:  # PIL 이 이미지로 못 읽는 경우
        raise HTTPException(status_code=400, detail=f"이미지를 읽을 수 없음: {e}") from e


class SearchBody(BaseModel):
    query: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=20)


@app.post("/search")
async def search(body: SearchBody):
    p = ready_pipe()

    def run():
        with lock:
            emb = p.embedder.encode([body.query])[0]
            return p.store.nearest(emb, body.k)

    return {"results": await run_in_threadpool(run)}


@app.get("/recent")
def recent(limit: int = 30, session: str | None = None):
    p = ready_pipe()
    return {"items": p.store.recent(limit=min(limit, 100), session=session), "total": p.store.count()}
