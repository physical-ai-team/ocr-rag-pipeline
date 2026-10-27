# 실시간 저장 현황 + RAG 검색 + Docker 통합

[01-기획](01-기획.md)의 5단계(저장 현황)·6단계(RAG)와, 기능별 서비스를 `docker compose` 로 묶은 방법을 정리한 문서.
2·3단계(QR·영상)는 [04-QR-영상전송](04-QR-영상전송.md), OCR·임베딩 로직은 `services/pipeline/app/pipeline.py` 참고.

## 한눈에 보기

```
폰 ─JPEG(WS)─▶ api ── frame_queue ── ocr_worker ─POST /process─▶ pipeline ─저장─▶ Supabase
                │                        │ ◀── {stored:[...], total} ──┘   (키 없으면 메모리)
                │                        └─ WS /api/ws/stored ─▶ 대시보드 ② 저장 현황
                │
대시보드 ③ ─POST /api/rag─▶ api ─POST /search─▶ pipeline (질문 임베딩 → top-k)
                              └─ 근거 문장 + 질문 ─▶ Gemini ─▶ 답변 [1][2]
```

- **컨테이너 2개**: `api`(QR·영상·저장현황·RAG, 8000번) + `pipeline`(OCR·임베딩·DB 저장, 8001번 · 밖에 안 열림).
- **VectorDB 는 Supabase(클라우드)** 라서 컨테이너가 없다. `.env` 에 키가 없으면 pipeline 이 메모리에 저장한다 (재시작하면 사라짐).
- 임베딩 모델은 pipeline 에만 올린다. RAG 질문도 pipeline 이 벡터로 바꾼다 (모델을 두 번 올리지 않게).

## 어디에 뭐가 있나

| 위치 | 내용 |
| --- | --- |
| `docker-compose.yml` | 두 컨테이너 정의, `.env` 연결, 모델 캐시 볼륨 |
| `.env.example` | 필요한 키 목록 → `.env` 로 복사해서 채움 |
| `services/pipeline/app/pipeline.py` | OCR → 문장 분리 → 임베딩 → 중복 검사 → 저장 (Embedding/DB 브랜치 코드) |
| `services/pipeline/app/main.py` | 위 로직을 HTTP 로 감싼 서버 (`/process`, `/search`, `/recent`, `/health`) |
| `services/api/app/storage.py` | `ocr_worker` (큐 → pipeline), 저장 현황 `GET /api/stored`, `WS /api/ws/stored` |
| `services/api/app/rag.py` | `POST /api/rag` (검색 + Gemini 답변) |
| `src/components/StorageStatus.js` | 대시보드 ② 패널 |
| `src/components/RagSearch.js` | 대시보드 ③ 패널 |
| `src/pages/Dashboard.js` | `/dashboard` — ①②③ 패널을 한 화면에 |

## 주소 규칙

### api (밖에서 부름)

| 주소 | 용도 |
| --- | --- |
| `GET /api/stored?limit=30` | `{items:[{id,text,meta}], total}` 최근 저장 문장 목록 |
| `GET /api/passages` | `{passages:[{no,title,sentences,first_ts,last_ts}], untitled_sentences, total_sentences}` 카드 제목으로 묶은 지문 목록 |
| `WS /api/ws/stored` | 서버 → 대시보드: `{"type":"stored","items":[...],"total":n}` (새로 저장될 때만) |
| `POST /api/rag` | `{"question":"...","k":5}` → `{answer, sources:[{n,id,text,score}], model}` |

`GEMINI_API_KEY` 가 없으면 `answer` 는 `null` 이고 근거 문장(`sources`)만 온다.

### pipeline (api 만 부름)

| 주소 | 용도 |
| --- | --- |
| `GET /health` | `{ready, load_error, store, total}` — 처음 몇 분은 모델 내려받느라 `ready:false` |
| `POST /process?session=..&frame_no=..` | 본문: JPEG → `{text, stored:[...], duplicates, ocr_ms, total_ms, total}` |
| `POST /search` | `{"query","k"}` → `{results:[{id,text,meta,score}]}` |
| `GET /recent?limit=30` | `{items, total}` |
| `GET /passages` | 지문 목록 (`app/passages.py`) |

모델 로드 중에는 `/process`·`/search`·`/recent` 가 `503` 을 준다. api 는 그동안 들어온 프레임을 버린다.

## 실행

### Docker 로 전체 실행 (추천)

```bash
copy .env.example .env      # 처음 한 번. 키는 팀 채팅으로 받아서 채운다 (비워 둬도 동작)
npm run build               # 프론트 빌드 → api 가 함께 서빙
docker compose up --build   # 처음엔 이미지 빌드 + 모델 다운로드로 10분 이상 걸릴 수 있다
```

- 대시보드: http://localhost:8000/dashboard
- pipeline 준비 확인: `docker compose logs -f pipeline` 에서 `[pipeline] 모델 로드 완료` 가 보이면 된다.
- 끄기: `Ctrl + C` 또는 `docker compose down`
- 코드를 고쳤으면 `docker compose up --build` 로 다시 빌드한다. 프론트만 고쳤으면 `npm run build` 만 다시 하면 된다.
- 폰으로 테스트할 때는 [04 문서](04-QR-영상전송.md)의 B 처럼 `cloudflared tunnel --url http://localhost:8000` 을 연다.

### 로컬에서 따로 실행 (코드 고치면서 볼 때)

```bash
conda activate ocr-rag
cd services/pipeline && uvicorn app.main:app --port 8001      # 터미널 1
cd services/api && uvicorn app.main:app --reload --port 8000  # 터미널 2
npm start                                                     # 터미널 3 → http://localhost:3000/dashboard
```

### 테스트

```bash
cd services/api && pytest        # 세션·영상 + 저장현황·RAG (pipeline·Gemini 는 가짜로 대체)
cd services/pipeline && pytest   # FAKE_MODELS=1 + 메모리 저장소라 모델 다운로드 없이 돈다
```

## 알아둘 점

- 처음 `docker compose up` 때 EasyOCR·임베딩 모델(합쳐서 수백 MB)을 내려받는다. Docker 볼륨(`model-cache`, `easyocr-models`)에 남아서 다음부터는 빠르다.
- pipeline 이미지는 torch 때문에 크다 (수 GB). Docker Desktop 디스크 공간을 확인한다.
- OCR 은 CPU 에서 프레임 하나에 몇 초 걸린다. 그동안 들어온 프레임은 `frame_queue`(최대 5장)에서 오래된 것부터 버려진다 → 항상 최신 화면을 처리한다.
- 같은 문장은 두 번 저장하지 않는다: 글자가 같으면 바로 거르고, OCR 오차로 조금 다르면 코사인 유사도 `DEDUP_SIM`(0.92) 이상일 때 거른다.
- 저장 현황 숫자는 **지문 수 / 100** 이다 (QR 세션이 아니라 DB 전체 기준). 목표 100 은 `StorageStatus.js` 의 `GOAL`.
  - OCR 이 카드 맨 위 제목 줄을 따로 떼서 문장마다 `meta.title` 로 저장하고, 같은 제목끼리 묶어 센다.
  - OCR 이 제목을 조금 틀리게 읽어도 (`Instrcctions For The New Eettle`) 글자가 80% 이상 같으면 같은 지문으로 합친다.
  - 카드 윗부분이 화면 밖이라 제목이 안 찍힌 문장은 "제목 미확인 문장"으로 따로 센다.
- Gemini 는 **무료 등급**(Google AI Studio)이라 분당·하루 요청 수 제한이 있고, 혼잡할 때 먼저 밀린다.
  그래서 가벼운 `GEMINI_MODEL`(기본 `gemini-3.5-flash-lite`)을 먼저 쓰고, 실패(503 혼잡·429 한도·20초 초과)하면
  `GEMINI_FALLBACK_MODEL`(기본 `gemini-3.6-flash`)로 한 번 더 시도한다. 둘 다 실패해도 근거 문장은 보여 준다.
  (`gemini-3.8-flash` 는 2026-10 확인 당시 무료 등급에서 503 이 자주 나서 기본값에서 뺐다)

## 앞으로 할 일

- [x] Supabase 키 받아서 `.env` 에 넣고 실제 DB 로 확인
- [x] Gemini 키 넣고 실제 답변 확인 (영어·한국어 질문, 없는 내용 질문)
- [ ] RAG 정확도 평가 세트 (`src/data/passages.js` 를 정답지로 질문 30~50개)
- [x] 문장 대신 "지문" 단위로 묶어서 저장 현황에 제목 표시
- [ ] 기존 `App.js` 랜딩 페이지와 `/dashboard` 연결 (프론트 담당과 상의)
