"""환경 변수 기반 설정. .env 파일이 있으면 자동으로 읽습니다."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent


def _f(name, default):
    return float(os.getenv(name, default))


# ── 03 OCR ──────────────────────────────────────────
OCR_ENGINE = os.getenv("OCR_ENGINE", "easyocr")       # easyocr | tesseract
USE_GPU = os.getenv("USE_GPU", "0") == "1"
OCR_MIN_CONF = _f("OCR_MIN_CONF", 0.40)               # 이 신뢰도 미만 조각은 버림
# EasyOCR 확대 배율: 1.5면 a·I·at 같은 짧은 단어를 덜 놓침 (CPU에서 프레임당 약 1.5배 느려짐, 1.0 = 확대 안 함)
OCR_MAG_RATIO = _f("OCR_MAG_RATIO", 1.5)
MIN_CHUNK_CHARS = int(os.getenv("MIN_CHUNK_CHARS", "20"))
FULL_SENTENCES = os.getenv("FULL_SENTENCES", "1") == "1"   # 프레임 가장자리에서 잘린 문장 버리기

# ── 04 임베딩 · VectorDB ────────────────────────────
# 다국어 모델: 영어 원문을 저장하고 한국어로 질문해도 검색됩니다 (384차원)
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")         # 서버 전용 service_role 키 (절대 커밋 금지)
COLLECTION = os.getenv("COLLECTION", "ocr_chunks")   # Supabase 테이블 이름
DEDUP_SIM = _f("DEDUP_SIM", 0.92)                     # 기존 문장과 이 이상 비슷하면 중복으로 보고 건너뜀

# 테스트용: 무거운 모델 대신 가짜 OCR/임베딩 사용
FAKE_MODELS = os.getenv("FAKE_MODELS", "0") == "1"


