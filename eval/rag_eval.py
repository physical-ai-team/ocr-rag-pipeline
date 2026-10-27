"""RAG 평가: eval/rag_questions.json 의 질문을 실행 중인 api 에 던지고 채점한다.

실행 (docker compose 가 떠 있고, 컨베이어 지문을 폰으로 찍어 DB 에 저장한 뒤):
    conda activate ocr-rag
    python eval/rag_eval.py                      # 기본 http://localhost:8000
    python eval/rag_eval.py --out eval/result.md # 결과를 마크다운 파일로도 저장

질문마다 세 단계로 나눠 채점한다. 틀렸을 때 어디가 문제인지(OCR / 검색 / LLM) 바로 보이게.
  1) 저장   그 지문이 DB 에 저장돼 있나          (/api/passages 의 제목과 비교)  → 아니면 OCR 이 아직 못 읽은 것
  2) 검색   근거 문장이 검색 결과 top-k 에 있나  (OCR 오타를 감안해 글자 80% 이상 일치)
  3) 답변   답에 정답 키워드가 하나라도 있나
passage 가 null 인 질문은 저장 안 된 내용을 물어서 "찾을 수 없다"고 답하는지(지어내지 않는지) 본다.

Gemini 무료 등급은 분당 요청 수 제한이 있어서 질문 사이에 --delay 초(기본 4초)씩 쉰다.
"""
import argparse
import difflib
import json
import re
import sys
import time
from pathlib import Path

import httpx

HERE = Path(__file__).parent


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def contains_fuzzy(source: str, evidence: str, threshold: float = 0.8) -> bool:
    """OCR 결과(source) 안에 근거 문장(evidence)이 대부분 들어 있나. 글자 몇 개 틀려도 인정."""
    ev, src = norm(evidence), norm(source)
    if not ev:
        return False
    matched = sum(b.size for b in difflib.SequenceMatcher(None, ev, src, autojunk=False).get_matching_blocks())
    return matched / len(ev) >= threshold


def title_stored(title: str, stored_titles: list[str]) -> bool:
    return any(difflib.SequenceMatcher(None, norm(title), norm(t)).ratio() >= 0.8 for t in stored_titles)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--delay", type=float, default=4.0, help="질문 사이 쉬는 초 (Gemini 무료 등급 분당 제한)")
    ap.add_argument("--out", help="결과 마크다운 저장 경로")
    args = ap.parse_args()
    # Windows 한글 콘솔(cp949)은 못 찍는 글자(°, 일부 기호)가 있어 그런 글자는 ? 로 바꿔 출력
    sys.stdout.reconfigure(errors="replace")

    questions = json.loads((HERE / "rag_questions.json").read_text(encoding="utf-8"))
    http = httpx.Client(base_url=args.api, timeout=90)
    stored_titles = [p["title"] for p in http.get("/api/passages").json()["passages"]]
    print(f"DB 에 저장된 지문 {len(stored_titles)}개 · 질문 {len(questions)}개\n")

    rows = []
    for i, q in enumerate(questions):
        if i:
            time.sleep(args.delay)
        t = time.time()
        r = http.post("/api/rag", json={"question": q["question"], "k": args.k}).json()
        ms = int((time.time() - t) * 1000)
        answer = r.get("answer") or ""
        correct = any(a.lower() in answer.lower() for a in q["answer_any"])
        if q["passage"] is None:
            row = {**q, "kind": "없는 내용", "stored": None, "hit": None, "correct": correct}
        else:
            hit = any(contains_fuzzy(s["text"], q["evidence"]) for s in r["sources"])
            stored = hit or title_stored(q["passage"], stored_titles)
            row = {**q, "kind": "지문", "stored": stored, "hit": hit, "correct": correct}
        row.update(answer=answer, model=r.get("model"), error=r.get("error"), ms=ms)
        rows.append(row)
        mark = "[미저장]" if row["stored"] is False else ("[정답]" if correct else "[오답]")
        print(f"{mark} #{q['id']:02d} {q['question']}\n      -> {answer.strip()[:120] or r.get('error')}  ({ms}ms)")

    report = summarize(rows, len(stored_titles))
    print("\n" + report)
    if args.out:
        Path(args.out).write_text(report + "\n\n" + details(rows), encoding="utf-8")
        print(f"\n결과 저장: {args.out}")


def pct(a: int, b: int) -> str:
    return f"{a}/{b} ({a / b:.0%})" if b else "-"


def summarize(rows: list[dict], n_titles: int) -> str:
    qs = [r for r in rows if r["kind"] == "지문"]
    stored = [r for r in qs if r["stored"]]
    neg = [r for r in rows if r["kind"] == "없는 내용"]
    lines = [
        "## RAG 평가 결과",
        "",
        f"- DB 에 저장된 지문: {n_titles}개",
        f"- 질문한 지문이 저장돼 있음 (OCR): {pct(len(stored), len(qs))}",
        f"- 저장된 것 중 근거 문장 검색 성공 (top-k): {pct(sum(r['hit'] for r in stored), len(stored))}",
        f"- 저장된 것 중 답변 정답: {pct(sum(r['correct'] for r in stored), len(stored))}",
        f"- 전체 질문 기준 답변 정답 (OCR 포함 end-to-end): {pct(sum(r['correct'] for r in qs), len(qs))}",
        f"- 없는 내용 질문에 '찾을 수 없음' 응답: {pct(sum(r['correct'] for r in neg), len(neg))}",
        f"- 평균 응답 시간: {sum(r['ms'] for r in rows) / max(len(rows), 1) / 1000:.1f}초",
    ]
    errors = [r for r in rows if r["error"]]
    if errors:
        lines.append(f"- LLM 응답 실패: {len(errors)}건 (무료 한도·혼잡일 수 있음, --delay 를 늘려 다시 실행)")
    return "\n".join(lines)


def details(rows: list[dict]) -> str:
    out = ["| # | 질문 | 저장 | 검색 | 정답 | 답변 |", "| --- | --- | --- | --- | --- | --- |"]
    yn = {True: "O", False: "X", None: "-"}
    for r in rows:
        ans = (r["answer"] or r["error"] or "").replace("\n", " ").replace("|", "/")[:100]
        out.append(f"| {r['id']} | {r['question']} | {yn[r['stored']]} | {yn[r['hit']]} | {yn[r['correct']]} | {ans} |")
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
