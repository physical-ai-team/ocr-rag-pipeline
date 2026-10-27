"""대시보드 ③ RAG 검색.

POST /api/rag  {"question": "...", "k": 5}
  → pipeline 에서 질문과 가까운 문장 top-k 를 찾고 → Gemini 가 그 문장들만 근거로 답한다.
  → {"answer": "...", "sources": [{"n":1,"id","text","score"}], "model": "...", "error": null}

GEMINI_API_KEY 가 없으면 answer 는 null 이고 검색된 문장(sources)만 돌려준다.
GEMINI_MODEL 이 실패하면(혼잡 503, 무료 한도 429, 시간 초과) GEMINI_FALLBACK_MODEL 로 한 번 더 시도하고,
그래도 실패하면 answer 는 null, error 에 이유를 담아 sources 는 그대로 돌려준다. (화면이 멈추지 않게)
"""
import asyncio
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .pipeline_client import pipeline

log = logging.getLogger("uvicorn.error")
router = APIRouter()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
# 무료 등급에서는 가벼운 모델이 빠르고 덜 막힌다. 모델마다 사용량 한도가 따로라 예비 모델이 도움이 된다
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.6-flash")
GEMINI_TIMEOUT_S = float(os.getenv("GEMINI_TIMEOUT_S", "20"))

SYSTEM_PROMPT = """너는 OCR 로 모은 영어 원문 문장들을 근거로 질문에 답하는 도우미다.
- 반드시 주어진 [번호] 문장들에 있는 내용만 근거로 답한다. 없는 내용은 지어내지 말고
  "저장된 내용에서 찾을 수 없습니다" (영어 질문이면 "I couldn't find this in the stored text.") 라고 답한다.
- 근거로 쓴 문장 번호를 [1], [2] 처럼 답 안에 표시한다.
- 질문과 같은 언어로 답한다. (한국어 질문이면 한국어로)
- OCR 결과라 철자가 조금 틀린 문장이 있을 수 있다."""

_gemini = None


def gemini():
    global _gemini
    if _gemini is None:
        from google import genai
        from google.genai import types
        _gemini = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=int(GEMINI_TIMEOUT_S * 1000)),
        )
    return _gemini


async def ask_gemini(model: str, prompt: str) -> str:
    from google.genai import types
    reply = await asyncio.wait_for(  # 서버 쪽 timeout 이 안 먹을 때를 대비한 이중 안전장치
        gemini().aio.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        ),
        timeout=GEMINI_TIMEOUT_S + 5,
    )
    return reply.text


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
        return {"answer": "아직 저장된 문장이 없습니다.", "sources": [], "model": None, "error": None}
    if not GEMINI_API_KEY:
        return {"answer": None, "sources": sources, "model": None, "error": None}

    context = "\n".join(f"[{s['n']}] {s['text']}" for s in sources)
    prompt = f"문장들:\n{context}\n\n질문: {body.question}"

    error = None
    for model in dict.fromkeys(m for m in (GEMINI_MODEL, GEMINI_FALLBACK_MODEL) if m):  # 순서 유지 + 중복 제거
        try:
            return {"answer": await ask_gemini(model, prompt), "sources": sources, "model": model, "error": None}
        except Exception as e:  # noqa: BLE001  혼잡(503), 무료 한도(429), 시간 초과, 키 오류 등
            error = "시간 초과" if isinstance(e, asyncio.TimeoutError) else str(e)[:200]
            log.warning("Gemini(%s) 호출 실패: %s", model, error)

    return {"answer": None, "sources": sources, "model": None, "error": f"LLM 응답 실패: {error}"}
