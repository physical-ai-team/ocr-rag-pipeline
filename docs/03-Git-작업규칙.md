# Git 작업 규칙

## 핵심: main에 직접 올리지 않는다

`main`은 항상 "돌아가는 상태"로 유지한다. 작업은 브랜치에서 하고 Pull Request(PR)로 합친다.

## 작업 순서

```bash
# 1. 최신 main 받기
git switch main
git pull

# 2. 작업용 브랜치 만들기
git switch -c feat/qr-pairing

# 3. 작업하고 커밋 (여러 번 해도 됨)
git add .
git commit -m "feat: QR 코드 생성 API 추가"

# 4. 브랜치를 GitHub에 올리기
git push -u origin feat/qr-pairing
```

5. GitHub 레포 페이지에서 **Compare & pull request** 버튼 → PR 생성 → 팀원 확인 후 **Merge**

## 브랜치 이름

| 접두어 | 용도 | 예시 |
| --- | --- | --- |
| `feat/` | 새 기능 | `feat/ocr-service`, `feat/rag-search` |
| `fix/` | 버그 수정 | `fix/qr-timeout` |
| `docs/` | 문서 | `docs/architecture` |
| `chore/` | 환경·설정 | `chore/dev-setup` |

## 커밋 메시지

`접두어: 무엇을 했는지` 형식. 예) `feat: 저장 현황 WebSocket 추가`, `fix: OCR 빈 프레임 예외 처리`

## 충돌이 났을 때

`git pull` 중 `CONFLICT`가 나면 파일 안의 `<<<<<<<`, `=======`, `>>>>>>>` 표시를 찾아
남길 내용만 남기고 **표시는 전부 지운 뒤** 커밋한다. 표시가 남은 채로 올리면 안 된다.
모르겠으면 커밋하지 말고 팀원에게 물어보기.
