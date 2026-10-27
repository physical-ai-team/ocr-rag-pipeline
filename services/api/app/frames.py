"""폰에서 받은 프레임을 OCR 쪽으로 넘기는 지점.

api는 프레임을 받으면 `frame_queue`에 넣는다. OCR 담당은 이 큐에서 꺼내 가면 된다.
OCR이 느려서 큐가 가득 차면 가장 오래된 프레임을 버린다. (실시간에서는 최신 프레임이 더 중요하다)
"""
import asyncio
import time
from dataclasses import dataclass


@dataclass
class Frame:
    sid: str
    ts: float
    image: bytes  # JPEG


class FrameQueue:
    def __init__(self, maxsize: int = 5) -> None:
        self._queue: asyncio.Queue[Frame] = asyncio.Queue(maxsize=maxsize)

    def put_latest(self, sid: str, image: bytes) -> None:
        if self._queue.full():
            self._queue.get_nowait()
        self._queue.put_nowait(Frame(sid=sid, ts=time.time(), image=image))

    async def get(self) -> Frame:
        return await self._queue.get()


frame_queue = FrameQueue()
