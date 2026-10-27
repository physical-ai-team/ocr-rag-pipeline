# ocr-rag-pipeline

OCR 및 벡터 임베딩 기반 영문 텍스트 추출·검색 파이프라인

- [처음 세팅 가이드 (conda 처음이면 여기부터)](docs/00-처음-세팅-가이드.md) · [기획](docs/01-기획.md) · [아키텍처·Docker 구성](docs/02-아키텍처-도커.md) · [Git 작업 규칙](docs/03-Git-작업규칙.md) · [QR·영상 전송](docs/04-QR-영상전송.md) · [저장 현황·RAG·Docker 실행](docs/05-저장현황-RAG-도커.md) · [시연 체크리스트](docs/06-시연-체크리스트.md)

## 전체 실행 (Docker)

Docker Desktop 을 켜 둔 상태에서:

```bash
copy .env.example .env      # 처음 한 번 (키는 팀 채팅으로 받아서 채우기, 비워 둬도 동작)
npm run build
docker compose up --build   # 처음엔 10분 이상 걸릴 수 있음
```

→ http://localhost:8000/dashboard

## 개발 환경 세팅 (처음 한 번만)

### 1. 프로그램 설치

| 프로그램 | 버전 | 다운로드 |
| --- | --- | --- |
| Git | 최신 | https://git-scm.com/downloads |
| Node.js | **20 LTS** | https://nodejs.org (20.x 버전 선택) |
| Miniforge (conda) | 최신 | https://github.com/conda-forge/miniforge/releases/latest |

> **conda를 처음 써보면 [처음 세팅 가이드](docs/00-처음-세팅-가이드.md)를 그대로 따라 하세요.** (설치 옵션, VS Code 연결, 자주 나는 오류까지 정리돼 있음)

설치 확인:

```bash
git --version
node --version    # v20.x.x 가 나와야 함
conda --version
```

### 2. 프로젝트 받기

```bash
git clone <레포 주소>
cd ocr-rag-pipeline
```

### 3. Python 가상환경 만들기

```bash
conda env create -f environment.yml
```

### 4. 프론트엔드 패키지 설치

```bash
npm ci
```

> `npm install`이 아니라 `npm ci`를 쓰세요. `package-lock.json`과 똑같은 버전으로 설치됩니다.

---

## 매일 작업할 때

```bash
git pull
conda activate ocr-rag    # 터미널 앞에 (ocr-rag) 가 보이면 성공
npm start                 # 프론트엔드 실행 → http://localhost:3000
```

## 누군가 패키지를 추가했다고 공지하면

```bash
git pull
conda env update -f environment.yml --prune   # Python 패키지
npm ci                                         # 프론트엔드 패키지
```

## 패키지를 추가하고 싶을 때 (규칙)

- **Python**: `pip install`만 하고 끝내지 말고, `environment.yml`의 `pip:` 아래에 `패키지명==버전`을 추가 → 커밋 → 팀에 공지
- **프론트엔드**: `npm install 패키지명` → 바뀐 `package.json`, `package-lock.json` 둘 다 커밋 → 팀에 공지

## 주의

- API 키 같은 비밀값은 `.env` 파일에 넣고 **절대 커밋하지 마세요** (`.gitignore`에 등록되어 있음).
- `git pull` 중 충돌(`<<<<<<<`, `=======`, `>>>>>>>`)이 나면 표시를 모두 지우고 정리한 뒤 커밋하세요. 표시가 남은 채로 올리지 마세요.
