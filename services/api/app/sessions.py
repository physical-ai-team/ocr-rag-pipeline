"""QR 세션 관리: 세션 발급, 만료, 폰/대시보드 연결 상태를 메모리에 보관한다."""
import os
import secrets
import time
from dataclasses import dataclass, field

from fastapi import WebSocket

SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "1800"))  # 기본 30분


@dataclass
class Session:
    sid: str
    expires_at: float
    phone: WebSocket | None = None
    dashboards: set[WebSocket] = field(default_factory=set)
    frames: int = 0
    latest: bytes | None = None
    last_push: float = 0.0

    @property
    def expired(self) -> bool:
        return time.time() > self.expires_at

    def status(self) -> dict:
        return {
            "type": "status",
            "phone_connected": self.phone is not None,
            "frames": self.frames,
        }

    async def broadcast(self) -> None:
        """대시보드들에게 현재 상태를 보낸다. 끊긴 대시보드는 목록에서 뺀다."""
        for ws in list(self.dashboards):
            try:
                await ws.send_json(self.status())
            except Exception:
                self.dashboards.discard(ws)


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        self._purge()
        # 8글자 정도의 추측하기 어려운 랜덤 값
        session = Session(
            sid=secrets.token_urlsafe(6),
            expires_at=time.time() + SESSION_TTL_SECONDS,
        )
        self._sessions[session.sid] = session
        return session

    def get(self, sid: str) -> Session | None:
        session = self._sessions.get(sid)
        if session is None or session.expired:
            return None
        return session

    def _purge(self) -> None:
        for sid in [s for s, v in self._sessions.items() if v.expired and v.phone is None]:
            del self._sessions[sid]


store = SessionStore()
