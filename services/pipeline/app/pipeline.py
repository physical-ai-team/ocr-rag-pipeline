"""03 OCR → 04 임베딩 · VectorDB 저장.

"""
from __future__ import annotations

import hashlib
import io
import json
import re
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
        """이미지 → [(줄 텍스트, 신뢰도 0~1)] (위→아래, 왼→오 순서)"""
        if config.FAKE_MODELS:
            return [(getattr(img, "fake_text", ""), 0.99)]

        if self.engine == "easyocr":
            res = self._reader.readtext(np.array(img), detail=1, paragraph=False)
            # 박스 왼쪽 위 좌표로 읽기 순서 정렬 (같은 줄 판정은 높이의 절반 기준)
            items = []
            for box, text, conf in res:
                ys = [p[1] for p in box]
                xs = [p[0] for p in box]
                h = max(ys) - min(ys) or 1
                items.append((min(ys), min(xs), h, text, float(conf)))
            items.sort(key=lambda t: (t[0], t[1]))
            lines, cur, cur_y, cur_h = [], [], None, None
            for y, x, h, text, conf in items:
                if cur and abs(y - cur_y) > cur_h * 0.5:
                    lines.append(cur)
                    cur = []
                if not cur:
                    cur_y, cur_h = y, h
                cur.append((x, text, conf))
            if cur:
                lines.append(cur)
            out = []
            for ln in lines:
                ln.sort(key=lambda t: t[0])
                out.append((" ".join(t[1] for t in ln), sum(t[2] for t in ln) / len(ln)))
            return out

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


def clean_text(lines: list[tuple[str, float]]) -> str:
    kept = [t for t, c in lines if c >= config.OCR_MIN_CONF and is_english(t)]
    text = " ".join(kept)
    text = re.sub(r"(\w)-\s+(\w)", r"\1\2", text)   # 줄바꿈 하이픈 합치기
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
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

    def process_frame(self, jpeg: bytes, session: str, frame_no: int, img=None) -> dict:
        t0 = time.time()
        img = img or self.decode(jpeg)

        # 03 OCR
        lines = self.ocr.read(img)
        text = clean_text(lines)
        t_ocr = time.time()

        result = {"frame_no": frame_no, "raw_lines": len(lines), "text": text,
                  "stored": [], "duplicates": 0, "ocr_ms": int((t_ocr - t0) * 1000)}
        sentences = split_sentences(text)
        fresh = [s for s in sentences if normalize(s) not in self._seen]
        result["duplicates"] += len(sentences) - len(fresh)
        if not fresh:
            result["total_ms"] = int((time.time() - t0) * 1000)
            return result

        # 04 임베딩 → 중복 검사 → 저장
        embs = self.embedder.encode(fresh)
        for sent, emb in zip(fresh, embs):
            near = self.store.nearest(emb, 1)
            if near and near[0]["score"] >= config.DEDUP_SIM:
                result["duplicates"] += 1
                self._seen.add(normalize(sent))
                continue
            meta = {"session": session, "ts": time.time(), "frame_no": frame_no,
                    "chars": len(sent), "source": "phone_camera_ocr"}
            _id = self.store.add(sent, emb, meta)
            self._seen.add(normalize(sent))
            result["stored"].append({
                "id": _id, "text": sent, "meta": meta, "dim": len(emb),
                "vector_preview": [round(x, 4) for x in emb[:8]],
                "nearest_score": near[0]["score"] if near else None,
            })
        result["total_ms"] = int((time.time() - t0) * 1000)
        return result
