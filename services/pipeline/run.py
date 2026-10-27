"""실행: python run.py <이미지 파일 또는 폴더> [...]

이미지마다 OCR → 문장 분리 → 임베딩 → 중복 검사 → Supabase 저장을 수행하고 결과를 출력합니다.
"""
import sys
from pathlib import Path

from app.pipeline import Pipeline

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def iter_images(args: list[str]):
    for a in args:
        p = Path(a)
        if p.is_dir():
            yield from sorted(f for f in p.iterdir() if f.suffix.lower() in IMAGE_EXTS)
        else:
            yield p


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    pipe = Pipeline()
    pipe.load()
    if not pipe.ready:
        sys.exit(f"모델 로드 실패: {pipe.load_error}")

    for frame_no, path in enumerate(iter_images(sys.argv[1:]), 1):
        r = pipe.process_frame(path.read_bytes(), session="cli", frame_no=frame_no)
        print(f"\n[{path.name}] OCR {r['ocr_ms']}ms · 전체 {r['total_ms']}ms · "
              f"저장 {len(r['stored'])} · 중복 {r['duplicates']}")
        print("  OCR:", r["text"] or "(인식된 영어 문장 없음)")
        for s in r["stored"]:
            print(f"  + {s['id']}  {s['text']}  (최근접 유사도 {s['nearest_score']})")

    print(f"\nDB 총 {pipe.store.count()}개 문장")
