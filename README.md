# OCR · 벡터 임베딩 파이프라인

PC 화면에 띄운 영어 원문을 휴대폰 카메라로 실시간 촬영하면, 서버가 글자를 읽어(OCR) 문장 단위로 벡터화해 VectorDB에 저장하고, 저장된 내용으로 질문에 답하는(RAG) 시스템입니다.

```
① PC 웹페이지 (영어 원문 송출)
        │  휴대폰이 화면을 촬영
② 휴대폰 카메라 ──JPEG 프레임(WebSocket)──▶ FastAPI 서버
                                              │
                         ③ OCR (EasyOCR / Tesseract)
                         ④ 문장 분리 → 임베딩 (Sentence-Transformers)
                                              │
                                     ⑤ ChromaDB 저장 ──이벤트(WebSocket)──▶ PC 대시보드 실시간 표시
                                              │
                         ⑥ 질문 → 임베딩 → top-k 검색 → LLM 답변
```

## 필수 요구사항과 구현 위치

| 단계 | 요구사항 | 구현 방법 | 코드 |
|---|---|---|---|
| 01 | 웹페이지와 휴대폰을 QR로 연결 | 서버가 세션 ID를 만들고 `https://<PC LAN IP>:8443/mobile?s=<세션>` 을 QR로 생성. 휴대폰이 이 주소로 들어오면 같은 세션에 묶임 | `main.py` `new_session()` |
| 02 | 휴대폰 카메라 영상을 실시간 전달 | `getUserMedia`로 후면 카메라를 열고 canvas로 초당 2~8장 JPEG를 떠서 WebSocket(`/ws/camera/{세션}`)으로 전송. 서버는 PC 대시보드로 최대 6fps 중계 | `mobile.html`, `main.py` `camera_ws()` |
| 03 | 영상 속 영어 원문을 텍스트로 추출 | 1.5초마다 **가장 최신 프레임만** OCR (밀린 프레임은 버려 지연이 쌓이지 않음). 신뢰도·영문 비율로 잡음 제거, 하이픈 줄바꿈 복원, 문장 분리, 화면 가장자리에서 잘린 문장 제거 | `pipeline.py` `OCREngine`, `clean_text()`, `split_sentences()` |
| 04 | 추출 텍스트와 임베딩 벡터를 DB에 저장 | 문장마다 384차원 정규화 벡터 생성 → 기존 문장과 코사인 유사도 0.92 이상이면 중복으로 건너뜀 → ChromaDB에 `문장 + 벡터 + 메타데이터(세션, 시각, 프레임 번호)` 저장 | `pipeline.py` `Embedder`, `VectorStore`, `process_frame()` |
| 05 | 저장 현황을 웹페이지에 실시간 표시 | 서버가 `ocr_start / ocr / stored / stats` 이벤트를 대시보드 WebSocket으로 푸시. 저장된 문장, 벡터 앞 8개 값, 유사도, 누적 통계가 바로 나타남 | `main.py` `ocr_worker()`, `index.html` |
| 06 | 저장 내용으로 질문에 답변 | 질문 임베딩 → ChromaDB top-5 검색 → 근거 문장을 번호와 함께 LLM에 전달해 답변 생성 (출처 [1][2] 표기). API 키가 없으면 검색된 문장을 그대로 보여주는 추출형 답변 | `rag.py` |

임베딩 모델은 다국어 모델(`paraphrase-multilingual-MiniLM-L12-v2`)을 기본으로 써서, **영어 원문을 저장하고 한국어로 질문해도 검색됩니다.**

## 폴더 구조

```
ocr-rag-pipeline/
├── run.py              # 실행 진입점 (HTTPS 인증서 자동 생성 + 서버 시작)
├── requirements.txt
├── .env.example
├── app/
│   ├── config.py       # 모든 설정값 (환경 변수로 변경 가능)
│   ├── main.py         # FastAPI: QR, WebSocket, API
│   ├── pipeline.py     # OCR → 문장 분리 → 임베딩 → 중복 검사 → ChromaDB
│   ├── rag.py          # 검색 + LLM 답변
│   └── passages.py     # PC에 띄울 영어 원문 예시 4개
└── static/
    ├── index.html      # PC 대시보드 (①·01·02·03·05·06)
    └── mobile.html     # 휴대폰 카메라 페이지 (02)
```

## 실행 방법

Python 3.10 이상이 필요합니다.

```bash
cd ocr-rag-pipeline
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # 필요하면 LLM API 키 입력 (Windows: copy)
python run.py
```

1. PC 브라우저에서 `https://localhost:8443` 접속 → 자체 서명 인증서 경고가 나오면 **고급 → 계속 진행**.
2. 오른쪽 QR을 휴대폰 카메라로 찍어 접속 → 마찬가지로 경고에서 **계속 진행** → **카메라 시작** → 권한 허용.
3. 휴대폰으로 왼쪽 원문 시트를 파란 모서리 표시 안에 꽉 차게 비춥니다.
4. 오른쪽에 카메라 화면, OCR 결과, 저장되는 문장이 실시간으로 쌓이는 것을 확인합니다.
5. 아래 RAG 검색 칸에 질문합니다. 예: “꿀벌 정찰병은 새 둥지를 어떻게 알리나요?”, “What is thermohaline circulation?”

첫 실행 때 EasyOCR 모델과 임베딩 모델을 내려받느라 몇 분 걸릴 수 있습니다. 대시보드에 “모델을 불러오는 중” 문구가 사라지면 준비된 것입니다.

## 자주 생기는 문제

**휴대폰에서 카메라가 안 열림.** 휴대폰 브라우저는 HTTPS 주소에서만 카메라를 허용합니다. 주소가 `https://`인지 확인하세요. iOS Safari가 자체 서명 인증서를 계속 막으면 ngrok을 쓰는 게 가장 간단합니다.
```bash
ngrok http https://localhost:8443
# 나온 주소를 .env 에 PUBLIC_URL=https://xxxx.ngrok-free.app 으로 넣고 run.py 재시작
```

**QR로 접속이 안 됨.** PC와 휴대폰이 같은 Wi‑Fi인지, PC 방화벽이 8443 포트를 막고 있지 않은지 확인하세요. 학교·회사 Wi‑Fi는 기기 간 통신을 막는 경우가 많아 이때도 ngrok이 해결책입니다. QR 아래 주소의 IP가 엉뚱하면(가상 어댑터 IP 등) `PUBLIC_URL`로 직접 지정합니다.

**OCR 결과가 엉망.** 원문 시트의 `가+` 버튼으로 글자를 키우고, 화면 밝기를 올리고, 모니터와 수직으로 가까이 찍으세요. 모니터 줄무늬(모아레)가 심하면 살짝 비스듬히 찍으면 나아집니다. 빠른 속도가 필요하면 `OCR_ENGINE=tesseract`(Tesseract 별도 설치 필요), GPU가 있으면 `USE_GPU=1`.

**같은 문장이 여러 번 저장됨 / 다른 문장이 안 저장됨.** `DEDUP_SIM` 값을 조정하세요. 올리면(예 0.96) 덜 걸러지고, 내리면(예 0.88) 더 많이 걸러집니다.

## 설계 메모 (보고서에 쓰기 좋은 부분)

영상 전송은 WebRTC 대신 **WebSocket + JPEG 프레임** 방식을 택했습니다. OCR에는 연속 영상이 아니라 선명한 정지 프레임이 필요하고, 시그널링 서버·STUN 없이 같은 네트워크에서 바로 동작하며, 서버가 프레임을 그대로 PC로 중계할 수 있어 구조가 단순합니다. 휴대폰 쪽은 `bufferedAmount`가 1MB를 넘으면 프레임을 건너뛰어 네트워크가 느려도 지연이 쌓이지 않습니다.

서버는 들어오는 모든 프레임을 OCR 하지 않고, 정해진 간격마다 **가장 최근 프레임 하나만** 처리합니다. 초당 4장이 들어와도 OCR은 1.5초에 한 번이므로 CPU만으로도 실시간성이 유지됩니다.

같은 화면을 계속 비추면 같은 문장이 반복해서 인식되므로 중복 제거를 두 단계로 합니다. 정규화한 문자열이 이미 본 것이면 임베딩 없이 바로 건너뛰고, OCR 오차로 한두 글자 다른 경우는 VectorDB에서 가장 가까운 문장과의 코사인 유사도로 걸러냅니다. 이때 쓰는 최근접 검색이 RAG 검색과 같은 연산이라 별도 인프라가 필요 없습니다.

ChromaDB는 기본 L2 거리를 쓰지만 벡터를 단위 길이로 정규화해 저장하므로 `코사인 유사도 = 1 − (제곱 L2 거리)/2` 로 정확히 환산됩니다.

## API 요약

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/api/session` | 새 세션 + QR 이미지(base64) |
| WS | `/ws/camera/{sid}` | 휴대폰 → 서버 JPEG 프레임 |
| WS | `/ws/dashboard/{sid}` | 서버 → PC 프레임 미리보기(바이너리) + 이벤트(JSON) |
| GET | `/api/records?limit=30` | 저장된 문장·메타데이터·벡터 미리보기 |
| DELETE | `/api/records` | DB 비우기 |
| POST | `/api/ask` | `{"question": "..."}` → 답변 + 근거 문장 + 유사도 |
| GET | `/api/health` | 모델 로드 상태, DB 개수, QR에 쓰는 주소 |

## 확장 아이디어

여러 문단을 섞어 찍었을 때 문서 단위로 묶는 기능(제목 OCR로 문서 ID 부여), 하이브리드 검색(BM25 + 벡터), 저장된 벡터를 2차원으로 줄여(UMAP) 대시보드에 점으로 찍는 시각화, 페이지 전체를 이어 붙인 뒤 문장 대신 2~3문장 슬라이딩 윈도우로 청크를 만드는 방식 비교 실험 등을 추가할 수 있습니다.
