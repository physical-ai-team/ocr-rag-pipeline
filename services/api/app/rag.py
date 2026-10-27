"""대시보드 ③ RAG 검색.

POST /api/rag  {"question": "...", "k": 5}
  → pipeline 에서 질문과 가까운 문장 top-k 를 찾고 → Gemini 가 그 문장들만 근거로 답한다.
  → {"answer": "...", "sources": [{"n":1,"id","text","score"}], "model": "..."}

GEMINI_API_KEY 가 없으면 answer 는 null 이고 검색된 문장(sources)만 돌려준다.
"""
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .pipeline_client import pipeline

log = logging.getLogger("uvicorn.error")
router = APIRouter()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

SYSTEM_PROMPT = """너는 OCR 로 모은 영어 원문 문장들을 근거로 질문에 답하는 도우미다.
- 반드시 주어진 [번호] 문장들에 있는 내용만 근거로 답한다. 없는 내용은 지어내지 말고 "저장된 내용에서 찾을 수 없습니다"라고 답한다.
- 근거로 쓴 문장 번호를 [1], [2] 처럼 답 안에 표시한다.
- 질문과 같은 언어로 답한다. (한국어 질문이면 한국어로)
- OCR 결과라 철자가 조금 틀린 문장이 있을 수 있다."""

_gemini = None


def gemini():
    global _gemini
    if _gemini is None:
        from google import genai
        _gemini = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini


class RagBody(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    k: int = Field(default=5, ge=1, le=10)


@router.post("/api/rag")
async def rag(body: RagBody):
    try:
        res = await pipeline.post("/search", json={"query": body.question, "k": body.k})
    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail="pipeline 서비스에 연결할 수 없습니다") from e
    if res.status_code != 200:
        raise HTTPException(status_code=503, detail=res.json().get("detail", "pipeline 준비 중"))

    sources = [
        {"n": i, "id": r["id"], "text": r["text"], "score": r["score"]}
        for i, r in enumerate(res.json()["results"], 1)
    ]
    if not sources:
        return {"answer": "아직 저장된 문장이 없습니다.", "sources": [], "model": None}
    if not GEMINI_API_KEY:
        return {"answer": None, "sources": sources, "model": None}

    context = "\n".join(f"[{s['n']}] {s['text']}" for s in sources)
    from google.genai import types

    try:
        reply = await gemini().aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"문장들:\n{context}\n\n질문: {body.question}",
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        )
    except Exception as e:  # noqa: BLE001  키 오류, 사용량 초과 등
        log.warning("Gemini 호출 실패: %s", e)
        raise HTTPException(status_code=502, detail=f"LLM 호출 실패: {e}") from e

    return {"answer": reply.text, "sources": sources, "model": GEMINI_MODEL}
