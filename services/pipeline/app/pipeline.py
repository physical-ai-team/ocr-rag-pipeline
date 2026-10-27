"""03 OCR → 04 임베딩 · VectorDB 저장.

"""
from __future__ import annotations

import hashlib
import io
import json
import re
import string
import time
import uuid

import numpy as np
from PIL import Image, ImageOps

from . import config

# ════════════════════════════════════════════════════
# OCR
# ════════════════════════════════════════════════════
class OCREngine:
    def __init__(self, engine: str):
        self.engine = engine
        self._reader = None

    def load(self):
        if config.FAKE_MODELS:
            return
        if self.engine == "easyocr":
            import easyocr
            self._reader = easyocr.Reader(["en"], gpu=config.USE_GPU, verbose=False)
        elif self.engine == "tesseract":
            import pytesseract
            pytesseract.get_tesseract_version()  # 설치 여부 확인
            self._reader = pytesseract
        else:
            raise ValueError(f"알 수 없는 OCR_ENGINE: {self.engine}")

    def read(self, img: Image.Image) -> list[tuple[str, float]]:
        """이미지 → [(줄 텍스트, 신뢰도 0~1)] (열 순서대로, 열 안에서는 위→아래)"""
        return [ln for col in self.read_columns(img) for ln in col]

    def read_columns(self, img: Image.Image) -> list[list[tuple[str, float]]]:
        """이미지 → 열(카드)별 줄 목록. 화면에 카드가 여러 장 나란히 있어도 서로 섞이지 않게 함"""
        if config.FAKE_MODELS:
            return [[(getattr(img, "fake_text", ""), 0.99)]]

        if self.engine == "easyocr":
            res = self._reader.readtext(np.array(img), detail=1, paragraph=False,
                                        mag_ratio=config.OCR_MAG_RATIO)
            items = []
            for box, text, conf in res:
                ys = [p[1] for p in box]
                xs = [p[0] for p in box]
                items.append((min(ys), min(xs), max(xs), max(ys) - min(ys) or 1, text, float(conf)))

            # 1) 가로 범위가 겹치는 박스끼리 같은 열로 묶음 (카드 사이 빈 공간에서 열이 갈림)
            items.sort(key=lambda t: t[1])
            cols, col_right = [], None
            for it in items:
                if cols and it[1] <= col_right:
                    cols[-1].append(it)
                    col_right = max(col_right, it[2])
                else:
                    cols.append([it])
                    col_right = it[2]

            # 화면 좌우 끝에서 잘린 카드는 버림: 이미지 가장자리에 닿거나, 다른 카드보다 눈에 띄게 좁은 열
            # (컨베이어가 움직이면 다음 프레임에서 카드가 온전히 보일 때 다시 읽힘)
            if config.FULL_SENTENCES:
                cols = self._drop_cut_columns(cols, img.size[0])

            # 2) 열 안에서 박스 왼쪽 위 좌표로 읽기 순서 정렬 (같은 줄 판정은 높이의 절반 기준)
            out = []
            for col in cols:
                col.sort(key=lambda t: (t[0], t[1]))
                lines, line_ys, cur, cur_y, cur_h = [], [], [], None, None
                for y, x, _, h, text, conf in col:
                    if cur and abs(y - cur_y) > cur_h * 0.5:
                        lines.append(cur)
                        cur = []
                    if not cur:
                        cur_y, cur_h = y, h
                        line_ys.append(y)
                    cur.append((x, text, conf))
                if cur:
                    lines.append(cur)
                col_lines = []
                for ln in lines:
                    ln.sort(key=lambda t: t[0])
                    col_lines.append((" ".join(t[1] for t in ln), sum(t[2] for t in ln) / len(ln)))
                out.append(mark_paragraph_ends(col_lines, line_ys))
            return out

        return [self._read_tesseract(img)]

    @staticmethod
    def _drop_cut_columns(cols: list[list[tuple]], img_w: int) -> list[list[tuple]]:
        margin = img_w * 0.01
        span = lambda col: (min(it[1] for it in col), max(it[2] for it in col))
        # 줄이 3개 이상인 열(=본문 카드)의 가장 넓은 폭을 기준으로 삼음
        widths = [x1 - x0 for col in cols if len(col) >= 3 for x0, x1 in [span(col)]]
        full_w = max(widths, default=0)
        kept = []
        for col in cols:
            x0, x1 = span(col)
            if x0 <= margin or x1 >= img_w - margin:
                continue
            if len(widths) >= 2 and x1 - x0 < full_w * 0.75:
                continue
            kept.append(col)
        return kept

    def _read_tesseract(self, img: Image.Image) -> list[tuple[str, float]]:
        # tesseract: 단어 단위 결과를 줄 단위로 묶음
        from pytesseract import Output
        d = self._reader.image_to_data(img.convert("L"), lang="eng", output_type=Output.DICT)
        groups: dict[tuple, list] = {}
        for i, word in enumerate(d["text"]):
            conf = float(d["conf"][i])
            if not word.strip() or conf < 0:
                continue
            key = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
            groups.setdefault(key, []).append((word, conf / 100))
        return [(" ".join(w for w, _ in ws), sum(c for _, c in ws) / len(ws))
                for _, ws in sorted(groups.items())]


# ════════════════════════════════════════════════════
# 텍스트 정리 · 문장 분리
# ════════════════════════════════════════════════════
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")


def is_english(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 5:
        return False
    return sum(c.isascii() for c in letters) / len(letters) >= 0.9


def is_heading(text: str) -> bool:
    """마침표 없이 대문자로만 된 줄 = 카드 제목 (예: THE QUIET MACHINERY OF CITIES)"""
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and all(c.isupper() for c in letters) and not re.search(r"[.!?]\s*$", text)


_ENDS_SENTENCE = re.compile(r"[.!?][\"')\]]?\s*$")
_TITLE_SMALL_WORDS = {"a", "an", "and", "at", "for", "from", "in", "of", "on", "or", "the", "to", "with"}
# 문장 첫머리에 자주 오는 단어. 소문자 단어 바로 뒤에 이게 대문자로 나오면 OCR 이 마침표를 놓친 것으로 본다
# ('beauty A pen' → 'beauty. A pen'). 고유명사(Thursday, China…)는 목록에 없어서 건드리지 않는다
_SENTENCE_STARTERS = ("A|An|The|They|It|He|She|We|You|This|That|These|Those|There|Its|His|Her|Their|Our|My|"
                      "In|On|At|For|But|If|When|After|Before|Nobody|Everyone|Nothing|Everything")
_MISSED_PERIOD = re.compile(rf"(?<=[a-z])\s+(?=(?:{_SENTENCE_STARTERS})\s+[a-z])")


def end_sentence(text: str) -> str:
    """줄 끝을 문장 끝으로 만든다. OCR 이 마침표를 : ; _ , 로 읽었으면 바꾸고, 없으면 붙인다."""
    return text.rstrip(" \t:;_,") + "."


def is_title_line(text: str) -> bool:
    """카드 제목 줄인지: 마침표로 끝나지 않고, 단어가 (짧은 관사·전치사 빼고) 모두 대문자로 시작.
    카드 제목은 대문자로 표시되지만 OCR 이 'How BREAD FAILS', 'ON Losing Things' 처럼 섞어 읽어서
    is_heading(전부 대문자)만으로는 놓친다."""
    if _ENDS_SENTENCE.search(text):
        return False
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'’]*", text)]
    if not words or sum(len(w) for w in words) < 3:
        return False
    return is_heading(text) or all(w[0].isupper() or w.lower() in _TITLE_SMALL_WORDS for w in words)


def mark_paragraph_ends(lines: list[tuple[str, float]], ys: list[float]) -> list[tuple[str, float]]:
    """줄 간격이 유난히 넓은 곳(= 문단이 바뀌는 곳) 앞 줄이 마침표로 안 끝나면 마침표를 붙인다.
    문단 끝의 짧은 단어(예: 'hand.')를 OCR 이 놓치면 두 문단이 한 문장으로 합쳐지는 것을 막는다."""
    if len(lines) < 3 or len(ys) != len(lines):
        return lines
    gaps = [b - a for a, b in zip(ys, ys[1:])]
    pitch = sorted(gaps)[(len(gaps) - 1) // 2]   # 보통 줄 간격 (중앙값, 짝수 개면 작은 쪽: 문단 간격이 기준이 되지 않게)
    out = list(lines)
    for i, gap in enumerate(gaps):
        text, conf = out[i]
        if pitch > 0 and gap > pitch * 1.25 and not _ENDS_SENTENCE.search(text) and not is_title_line(text):
            out[i] = (end_sentence(text), conf)
    return out


def clean_card(lines: list[tuple[str, float]]) -> tuple[str | None, str]:
    """카드(열) 하나의 줄 목록 → (제목, 본문 텍스트). 제목이 안 보이면 None."""
    kept = []
    for t, c in lines:
        if c >= config.OCR_MIN_CONF and is_english(t):
            kept.append(t)
        elif kept and _ENDS_SENTENCE.search(t) and not _ENDS_SENTENCE.search(kept[-1]):
            # 버리는 줄(예: 신뢰도 낮은 'hand.')이 문장 끝이었으면 그 경계는 남긴다
            kept[-1] = end_sentence(kept[-1])
    title_lines = []
    while kept and len(title_lines) < 3 and is_title_line(kept[0]):   # 맨 위 제목 줄(최대 3줄)은 따로 뺀다
        title_lines.append(kept.pop(0))
    # OCR 이 대소문자를 제각각 읽으므로 항상 같은 모양으로: 'ON Losing Things' → 'On Losing Things'
    # (str.title 은 "Cartographer's" 를 "Cartographer'S" 로 만들어서 capwords 를 쓴다)
    title = string.capwords(" ".join(title_lines)) if title_lines else None
    return title, _tidy(" ".join(kept))


def clean_text(lines: list[tuple[str, float]]) -> str:
    return clean_card(lines)[1]


def _tidy(text: str) -> str:
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)   # 줄바꿈 하이픈 합치기
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    # EasyOCR이 마침표를 : ; _ 로 잘못 읽는 경우 복원 (뒤에 대문자 단어가 오거나 맨 끝일 때)
    text = re.sub(r"[:;_](?=\s+[A-Z])", ".", text)
    text = re.sub(r"[:;_]\s*$", ".", text)
    text = re.sub(r"(\w)_", r"\1,", text)            # 나머지 _ 는 대부분 쉼표
    text = re.sub(r"(?<=[a-z] )&(?= [a-z])", "a", text)  # 소문자 단어 사이 & 는 대부분 a 를 잘못 읽은 것
    text = _MISSED_PERIOD.sub(". ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_SPLIT.split(text) if p.strip()]
    if config.FULL_SENTENCES and parts:
        # 화면 가장자리에서 잘린 문장은 버림: 끝이 마침표류가 아니거나, 소문자로 시작
        if not re.search(r"[.!?][\"')\]]?$", parts[-1]):
            parts = parts[:-1]
        if parts and parts[0][:1].islower():
            parts = parts[1:]
    return [p for p in parts if len(p) >= config.MIN_CHUNK_CHARS]


def normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())




# ════════════════════════════════════════════════════
# 임베딩
# ════════════════════════════════════════════════════
class Embedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.model = None
        self.dim = 384

    def load(self):
        if config.FAKE_MODELS:
            return
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(self.model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def encode(self, texts: list[str]) -> list[list[float]]:
        if config.FAKE_MODELS:  # 문자 trigram 해시 기반 가짜 벡터 (테스트용)
            out = []
            for t in texts:
                v = np.zeros(self.dim)
                s = normalize(t)
                for i in range(len(s) - 2):
                    v[int(hashlib.md5(s[i:i + 3].encode()).hexdigest(), 16) % self.dim] += 1
                out.append((v / (np.linalg.norm(v) or 1)).tolist())
            return out
        vecs = self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return vecs.tolist()


# ════════════════════════════════════════════════════
# VectorDB (Supabase + pgvector)
# ════════════════════════════════════════════════════
class VectorStore:
    """Supabase(PostgreSQL + pgvector) 테이블에 문장·벡터·메타데이터 저장.
    유사도 검색은 sql/supabase_schema.sql 의 match_<테이블> 함수(코사인 거리)를 RPC로 호출합니다."""

    def __init__(self, url: str, key: str, table: str):
        if not url or not key:
            raise RuntimeError("SUPABASE_URL / SUPABASE_KEY 가 설정되지 않았습니다 (.env 확인)")
        from supabase import create_client
        self.client = create_client(url, key)
        self.table = table

    def _t(self):
        return self.client.table(self.table)

    def count(self) -> int:
        r = self._t().select("id", count="exact", head=True).execute()
        return r.count or 0

    def nearest(self, emb: list[float], k: int = 1) -> list[dict]:
        r = self.client.rpc(f"match_{self.table}",
                            {"query_embedding": emb, "match_count": k}).execute()
        return [{"id": d["id"], "text": d["text"], "meta": d["meta"],
                 "score": round(float(d["similarity"]), 4)} for d in r.data]

    def add(self, text: str, emb: list[float], meta: dict) -> str:
        _id = uuid.uuid4().hex[:12]
        self._t().insert({"id": _id, "text": text, "embedding": emb, "meta": meta}).execute()
        return _id

    def recent(self, limit: int = 30, session: str | None = None) -> list[dict]:
        q = self._t().select("id, text, meta, embedding")
        if session:
            q = q.eq("meta->>session", session)
        r = q.order("created_at", desc=True).limit(limit).execute()
        rows = []
        for d in r.data:
            e = d["embedding"]
            if isinstance(e, str):  # pgvector는 "[0.1,0.2,...]" 문자열로 내려옴
                e = json.loads(e)
            rows.append({"id": d["id"], "text": d["text"], "meta": d["meta"],
                         "vector_preview": [round(float(x), 4) for x in e[:8]]})
        return rows

    def titles(self) -> list[dict]:
        """모든 문장의 (카드 제목, 저장 시각). 지문 단위 저장 현황용이라 벡터는 안 가져온다."""
        rows, page = [], 1000   # Supabase 는 한 번에 최대 1000행
        while True:
            r = (self._t().select("title:meta->>title, ts:meta->>ts")
                 .order("created_at").range(len(rows), len(rows) + page - 1).execute())
            rows += [{"title": d["title"], "ts": float(d["ts"] or 0)} for d in r.data]
            if len(r.data) < page:
                return rows

    def reset(self):
        self._t().delete().neq("id", "").execute()


class MemoryStore:
    """Supabase 키가 없을 때 쓰는 메모리 저장소 (VectorStore 와 같은 메서드).
    서버를 껐다 켜면 내용이 사라지므로 개발·테스트용."""

    def __init__(self):
        self.rows: list[dict] = []

    def count(self) -> int:
        return len(self.rows)

    def nearest(self, emb: list[float], k: int = 1) -> list[dict]:
        q = np.array(emb)
        scored = [(float(np.dot(q, r["embedding"])), r) for r in self.rows]  # 정규화 벡터라 내적 = 코사인
        scored.sort(key=lambda t: t[0], reverse=True)
        return [{"id": r["id"], "text": r["text"], "meta": r["meta"], "score": round(s, 4)}
                for s, r in scored[:k]]

    def add(self, text: str, emb: list[float], meta: dict) -> str:
        _id = uuid.uuid4().hex[:12]
        self.rows.append({"id": _id, "text": text, "embedding": np.array(emb), "meta": meta})
        return _id

    def recent(self, limit: int = 30, session: str | None = None) -> list[dict]:
        rows = [r for r in self.rows if not session or r["meta"].get("session") == session]
        return [{"id": r["id"], "text": r["text"], "meta": r["meta"],
                 "vector_preview": [round(float(x), 4) for x in r["embedding"][:8]]}
                for r in reversed(rows[-limit:])]

    def titles(self) -> list[dict]:
        return [{"title": r["meta"].get("title"), "ts": r["meta"].get("ts", 0)} for r in self.rows]

    def reset(self):
        self.rows.clear()


def make_store():
    if config.SUPABASE_URL and config.SUPABASE_KEY:
        return VectorStore(config.SUPABASE_URL, config.SUPABASE_KEY, config.COLLECTION)
    print("[pipeline] SUPABASE_URL/KEY 가 없어 메모리 저장소를 씁니다 (재시작하면 사라짐)")
    return MemoryStore()


# ════════════════════════════════════════════════════
# 파이프라인
# ════════════════════════════════════════════════════
class Pipeline:
    def __init__(self):
        self.ocr = OCREngine(config.OCR_ENGINE)
        self.embedder = Embedder(config.EMBED_MODEL)
        self.store = make_store()
        self.ready = False
        self.load_error: str | None = None
        self._seen: set[str] = set()   # 정확히 같은 문장은 임베딩 전에 빠르게 거름

    def load(self):
        try:
            t = time.time()
            self.ocr.load()
            self.embedder.load()
            self.ready = True
            print(f"[pipeline] 모델 로드 완료 ({time.time() - t:.1f}s) "
                  f"OCR={self.ocr.engine} EMB={self.embedder.model_name} dim={self.embedder.dim}")
        except Exception as e:  # noqa: BLE001
            self.load_error = f"{type(e).__name__}: {e}"
            print("[pipeline] 모델 로드 실패:", self.load_error)

    @staticmethod
    def decode(jpeg: bytes) -> Image.Image:
        img = Image.open(io.BytesIO(jpeg))
        img = ImageOps.exif_transpose(img).convert("RGB")
        if max(img.size) > 1600:
            img.thumbnail((1600, 1600))
        return img

    def _already_seen(self, sent: str) -> bool:
        """이미 처리한 문장이거나, 이미 저장한 문장을 통째로 품은 '두 문장이 붙은' 버전이면 True."""
        n = normalize(sent)
        return n in self._seen or any(len(s) >= 20 and s in n for s in self._seen)

    def process_frame(self, jpeg: bytes, session: str, frame_no: int, img=None) -> dict:
        t0 = time.time()
        img = img or self.decode(jpeg)

        # 03 OCR
        cols = self.ocr.read_columns(img)
        cards = [(title, t) for title, t in (clean_card(c) for c in cols) if t]
        text = "\n".join(t for _, t in cards)
        t_ocr = time.time()

        result = {"frame_no": frame_no, "raw_lines": sum(len(c) for c in cols), "text": text,
                  "stored": [], "duplicates": 0, "ocr_ms": int((t_ocr - t0) * 1000)}
        # 열(카드)마다 따로 문장 분리 → 카드 경계에서 잘린 문장도 카드별로 버려짐. 문장마다 카드 제목을 같이 들고 간다
        sentences = [(s, title) for title, t in cards for s in split_sentences(t)]
        fresh = [(s, title) for s, title in sentences if not self._already_seen(s)]
        result["duplicates"] += len(sentences) - len(fresh)
        if not fresh:
            result["total_ms"] = int((time.time() - t0) * 1000)
            return result

        # 04 임베딩 → 중복 검사 → 저장
        embs = self.embedder.encode([s for s, _ in fresh])
        for (sent, title), emb in zip(fresh, embs):
            near = self.store.nearest(emb, 1)
            if near and near[0]["score"] >= config.DEDUP_SIM:
                result["duplicates"] += 1
                self._seen.add(normalize(sent))
                continue
            meta = {"session": session, "ts": time.time(), "frame_no": frame_no,
                    "chars": len(sent), "source": "phone_camera_ocr"}
            if title:
                meta["title"] = title
            _id = self.store.add(sent, emb, meta)
            self._seen.add(normalize(sent))
            result["stored"].append({
                "id": _id, "text": sent, "meta": meta, "dim": len(emb),
                "vector_preview": [round(x, 4) for x in emb[:8]],
                "nearest_score": near[0]["score"] if near else None,
            })
        result["total_ms"] = int((time.time() - t0) * 1000)
        return result
