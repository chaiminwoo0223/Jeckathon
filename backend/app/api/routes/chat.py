import asyncio
from collections import deque
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.api.deps import get_current_user
from app.core.db import engine

router = APIRouter(prefix="/chat", tags=["chat"])

ROOM_IDS = (1, 2)
HISTORY_SIZE = 50
MAX_TEXT = 500


class Room:
    """방 하나: 접속자, 최근 메시지, 브로드캐스트 워커(asyncio 작업 1개)."""

    def __init__(self, room_id: int) -> None:
        self.room_id = room_id
        self.clients: set[WebSocket] = set()
        self.history: deque[dict[str, Any]] = deque(maxlen=HISTORY_SIZE)
        self.queue: asyncio.Queue[dict[str, Any]] | None = None
        self.worker: asyncio.Task[None] | None = None

    def ensure_worker(self) -> None:
        # 첫 접속 때 실행 중인 이벤트 루프에서 띄운다(모듈 import 시점엔 루프가 없다)
        if self.worker is None or self.worker.done():
            self.queue = asyncio.Queue()
            self.worker = asyncio.create_task(self._broadcast())

    async def _broadcast(self) -> None:
        assert self.queue is not None
        while True:
            msg = await self.queue.get()
            self.history.append(msg)
            for ws in list(self.clients):
                try:
                    await ws.send_json(msg)
                except Exception:
                    self.clients.discard(ws)


# shortcut: 프로세스 메모리에 방을 둔다. 서버 워커 1개(`fastapi dev`, `--workers 1`)에서만 맞다. 여러 워커가 필요하면 Redis pub/sub로 바꾼다.
rooms = {room_id: Room(room_id) for room_id in ROOM_IDS}


@router.websocket("/rooms/{room_id}/ws")
async def chat_ws(websocket: WebSocket, room_id: int, token: str) -> None:
    room = rooms.get(room_id)
    if room is None:
        await websocket.close(code=1008)
        return
    # 브라우저 WebSocket은 Authorization 헤더를 못 붙여서 토큰을 쿼리로 받는다
    try:
        with Session(engine) as session:
            user = get_current_user(session, token)
            user_id, name = str(user.id), user.display_nickname
    except HTTPException:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    room.ensure_worker()
    for msg in list(room.history):
        await websocket.send_json(msg)
    room.clients.add(websocket)
    try:
        while True:
            text = (await websocket.receive_text()).strip()[:MAX_TEXT]
            if text and room.queue is not None:
                await room.queue.put(
                    {
                        "room_id": room_id,
                        "user_id": user_id,
                        "name": name,
                        "text": text,
                        "sent_at": datetime.now(UTC).isoformat(),
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        room.clients.discard(websocket)
