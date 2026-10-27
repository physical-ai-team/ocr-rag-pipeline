# CLAUDE.md

이 레포에서 작업하는 Claude(및 사람)를 위한 안내. 팀원들은 개발 환경에 익숙하지 않으니 설명과 문서는 한국어로, 쉽게 쓴다.

## 프로젝트

PC 웹페이지의 영어 원문을 휴대폰 카메라로 실시간 촬영 → OCR → 임베딩 → Vector DB 저장 → RAG 검색하는 파이프라인.

- 처음 세팅(conda 초보용): [docs/00-처음-세팅-가이드.md](docs/00-처음-세팅-가이드.md)
- 기획: [docs/01-기획.md](docs/01-기획.md)
- 아키텍처·Docker 구성(초안): [docs/02-아키텍처-도커.md](docs/02-아키텍처-도커.md)
- Git 규칙: [docs/03-Git-작업규칙.md](docs/03-Git-작업규칙.md)

## 현재 상태

- 프론트엔드: React 19 + CRA(`react-scripts`) + Stitches(`@stitches/react`) + `lucide-react`. 레포 루트의 `src/`. 아직 `src/App.js` 한 파일에 대부분 있음.
- 백엔드(OCR, 임베딩, Vector DB, API): 아직 없음. `services/<기능>/` 아래 기능별 Docker 컨테이너로 만들 예정.

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
```

## 규칙

- `main`에 직접 커밋/푸시하지 않는다. `feat/`, `fix/`, `docs/`, `chore/` 브랜치 → PR.
- 커밋 메시지: `feat: …`, `fix: …` 형식, 한국어.
- 머지 충돌 표시(`<<<<<<<` 등)가 남은 파일을 커밋하지 않는다.
- `.env`(API 키 등)는 커밋하지 않는다.
- 다른 팀원 담당 영역(예: 프론트엔드 `src/`)을 크게 구조 변경할 때는 먼저 물어본다.
