"""워커(프로세스) 사이 실시간 메시지 버스. Postgres LISTEN/NOTIFY를 쓴다.

`fastapi run --workers 4`는 프로세스 4개라 메모리를 공유하지 않는다. 그래서 WebSocket 연결이
워커마다 흩어진다. 워커마다 같은 채널을 LISTEN 하고, publish는 NOTIFY로 보낸다. 모든 워커가
같은 메시지를 커밋 순서대로 받아 자기 워커에 붙은 클라이언트에게 넘긴다. Redis는 쓰지 않는다.
"""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import psycopg

from app.core.config import settings

CHANNEL = "realtime"
# NOTIFY payload는 기본 설정에서 8000바이트 미만이어야 한다
MAX_PAYLOAD_BYTES = 7900

logger = logging.getLogger(__name__)

Handler = Callable[[dict[str, Any]], None]


def _conninfo() -> str:
    # SQLAlchemy용 "postgresql+psycopg://"를 psycopg가 읽는 "postgresql://"로
    return str(settings.DATABASE_URL).replace("+psycopg", "", 1)


class Bus:
    def __init__(self) -> None:
        self.handlers: dict[str, Handler] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._listener: asyncio.Task[None] | None = None
        self._ready: asyncio.Event | None = None
        self._pub: psycopg.AsyncConnection[Any] | None = None
        self._pub_lock: asyncio.Lock | None = None

    def subscribe(self, topic: str, handler: Handler) -> None:
        """topic 메시지를 받을 함수. 리스너 작업 안에서 불리니 막히지 않게 짠다."""
        self.handlers[topic] = handler

    async def start(self) -> None:
        """LISTEN이 걸릴 때까지 기다린다. 첫 접속 때 실행 중인 이벤트 루프에서 띄운다."""
        loop = asyncio.get_running_loop()
        if self._loop is not loop or self._listener is None or self._listener.done():
            self._loop = loop
            self._ready = asyncio.Event()
            self._pub = None
            self._pub_lock = asyncio.Lock()
            self._listener = asyncio.create_task(self._listen())
        assert self._ready is not None
        await asyncio.wait_for(self._ready.wait(), timeout=5)

    async def publish(self, topic: str, data: dict[str, Any]) -> None:
        payload = json.dumps({"topic": topic, "data": data}, ensure_ascii=False)
        if len(payload.encode()) > MAX_PAYLOAD_BYTES:
            raise ValueError("realtime payload too large")
        await self.start()
        assert self._pub_lock is not None
        # 연결 하나를 잠금으로 줄 세워 한 워커 안의 발행 순서를 지킨다
        async with self._pub_lock:
            if self._pub is None or self._pub.closed:
                self._pub = await psycopg.AsyncConnection.connect(
                    _conninfo(), autocommit=True
                )
            await self._pub.execute("SELECT pg_notify(%s, %s)", (CHANNEL, payload))

    async def _listen(self) -> None:
        # shortcut: 재접속하는 사이(약 1초)에 온 메시지는 잃는다. 기록이 필요해지면 테이블에 쓰고 id만 보낸다.
        while True:
            try:
                async with await psycopg.AsyncConnection.connect(
                    _conninfo(), autocommit=True
                ) as conn:
                    await conn.execute(f"LISTEN {CHANNEL}")
                    assert self._ready is not None
                    self._ready.set()
                    async for note in conn.notifies():
                        self._dispatch(note.payload)
            except Exception:
                logger.exception("realtime listener disconnected, retrying in 1s")
                await asyncio.sleep(1)

    def _dispatch(self, payload: str) -> None:
        try:
            msg = json.loads(payload)
            handler = self.handlers.get(msg["topic"])
            if handler is not None:
                handler(msg["data"])
        except Exception:
            logger.exception("realtime handler failed")


bus = Bus()
