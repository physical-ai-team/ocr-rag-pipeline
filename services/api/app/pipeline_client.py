"""pipeline 서비스(OCR·임베딩·저장)를 부르는 HTTP 클라이언트.

docker compose 안에서는 PIPELINE_URL=http://pipeline:8001, 로컬에서 따로 띄우면 기본값 localhost:8001.
"""
import os

import httpx

PIPELINE_URL = os.getenv("PIPELINE_URL", "http://localhost:8001")

# OCR 이 CPU 에서 몇 초 걸릴 수 있어서 넉넉하게
pipeline = httpx.AsyncClient(base_url=PIPELINE_URL, timeout=60)
