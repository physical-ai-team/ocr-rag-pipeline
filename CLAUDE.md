# CLAUDE.md

이 레포에서 작업하는 Claude(및 사람)를 위한 안내. 팀원들은 개발 환경에 익숙하지 않으니 설명과 문서는 한국어로, 쉽게 쓴다.

## 프로젝트

PC 웹페이지의 영어 원문을 휴대폰 카메라로 실시간 촬영 → OCR → 임베딩 → Vector DB 저장 → RAG 검색하는 파이프라인.

- 처음 세팅(conda 초보용): [docs/00-처음-세팅-가이드.md](docs/00-처음-세팅-가이드.md)
- 기획: [docs/01-기획.md](docs/01-기획.md)
- 아키텍처·Docker 구성: [docs/02-아키텍처-도커.md](docs/02-아키텍처-도커.md)
- Git 규칙: [docs/03-Git-작업규칙.md](docs/03-Git-작업규칙.md)
- QR·영상 전송(api): [docs/04-QR-영상전송.md](docs/04-QR-영상전송.md)
- 저장 현황·RAG·Docker 실행: [docs/05-저장현황-RAG-도커.md](docs/05-저장현황-RAG-도커.md)
- 시연 체크리스트: [docs/06-시연-체크리스트.md](docs/06-시연-체크리스트.md)
- RAG 평가: `eval/rag_questions.json`(질문·정답 42개), `python eval/rag_eval.py` (api 가 떠 있어야 함)

## 현재 상태

- 프론트엔드: React 19 + CRA(`react-scripts`). 레포 루트의 `src/`. 랜딩은 `App.js`(Stitches), 주소별 화면은 `index.js` 에서 고름: `/m` 폰 촬영, `/pair` QR, `/dashboard` ①QR ②저장 현황 ③RAG. 패널 컴포넌트는 `src/components/`(일반 CSS).
- `services/api`: FastAPI. QR 세션, 폰 프레임 WebSocket, `ocr_worker`(프레임 → pipeline), 저장 현황, RAG(Gemini).
- `services/pipeline`: FastAPI 로 감싼 OCR(EasyOCR) → 임베딩(sentence-transformers) → Supabase 저장. 키 없으면 메모리 저장소.
- `docker-compose.yml`: api(8000) + pipeline(내부 8001). 키는 루트 `.env` (`.env.example` 참고).

## 환경

- Node 20 (`.nvmrc`), 설치는 `npm ci` (`npm install`은 패키지 추가할 때만, 이후 `package-lock.json` 같이 커밋)
- Python: conda 환경 `ocr-rag` (`environment.yml`, Python 3.11). 패키지는 `environment.yml`에 `==` 버전 고정으로 추가
- 개발 OS: Windows (PowerShell)

## 명령어

```bash
npm start          # 프론트엔드 개발 서버 (http://localhost:3000)
npm run build      # 프로덕션 빌드 (변경 후 깨지지 않는지 확인용)
npm test           # 테스트
conda activate ocr-rag
cd services/api && pytest        # api 테스트 (pipeline·Gemini 는 가짜)
cd services/pipeline && pytest   # pipeline 테스트 (FAKE_MODELS, 모델 다운로드 없음)
docker compose up --build        # 전체 실행 (먼저 npm run build) → http://localhost:8000/dashboard
```

## 규칙

- `main`에 직접 커밋/푸시하지 않는다. `feat/`, `fix/`, `docs/`, `chore/` 브랜치 → PR.
- 커밋 메시지: `feat: …`, `fix: …` 형식, 한국어.
- 머지 충돌 표시(`<<<<<<<` 등)가 남은 파일을 커밋하지 않는다.
- `.env`(API 키 등)는 커밋하지 않는다. 새 키가 필요하면 `.env.example` 에 이름만 추가한다.
- Python 패키지는 해당 서비스의 `requirements.txt` 와 `environment.yml` 양쪽에 같은 `==` 버전으로 넣는다.
- `package-lock.json` 은 Node 20(npm 10)으로 만든다. 다른 버전으로 `npm install` 하면 lock 이 바뀌어 `npm ci` 가 깨진다.
- 다른 팀원 담당 영역(예: 프론트엔드 `src/`)을 크게 구조 변경할 때는 먼저 물어본다.
