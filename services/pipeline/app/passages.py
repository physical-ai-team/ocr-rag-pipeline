"""저장된 문장들을 카드 제목(meta.title)으로 묶어 '지문 단위' 저장 현황을 만든다.

OCR 이 같은 제목을 조금씩 다르게 읽는 경우가 있어서 ('Instrcctions For The New Eettle')
글자가 충분히 비슷한 제목은 같은 지문으로 합친다. 대표 제목은 가장 많이 나온 표기.
"""
import difflib
from collections import Counter

SAME_TITLE = 0.8  # 이 이상 비슷하면 같은 지문


def _key(title: str) -> str:
    return "".join(c for c in title.lower() if c.isalnum())


def group_passages(rows: list[dict]) -> dict:
    """rows: [{"title": str | None, "ts": float}] → 지문 목록 (처음 저장된 순서대로 번호)"""
    groups: list[dict] = []  # {"key", "names": Counter, "count", "first_ts", "last_ts"}
    untitled = 0
    for row in sorted(rows, key=lambda r: r["ts"]):
        title = (row.get("title") or "").strip()
        if not title:
            untitled += 1
            continue
        key = _key(title)
        group = next((g for g in groups if difflib.SequenceMatcher(None, key, g["key"]).ratio() >= SAME_TITLE), None)
        if group is None:
            group = {"key": key, "names": Counter(), "count": 0, "first_ts": row["ts"]}
            groups.append(group)
        group["names"][title] += 1
        group["count"] += 1
        group["last_ts"] = row["ts"]

    passages = [{"no": i, "title": g["names"].most_common(1)[0][0], "sentences": g["count"],
                 "first_ts": g["first_ts"], "last_ts": g["last_ts"]}
                for i, g in enumerate(groups, 1)]
    return {"passages": passages, "untitled_sentences": untitled, "total_sentences": len(rows)}
