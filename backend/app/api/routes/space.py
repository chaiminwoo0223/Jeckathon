import asyncio
import json
import random
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.api.deps import get_current_user
from app.core.db import engine
from app.models import CommunityMember
from app.services.space import CHAT_TEXT_MAX, H, W, hub

router = APIRouter(prefix="/communities", tags=["space"])

EMOTES = {"clap", "cheer", "wave", "fire"}
MOVE_INTERVAL = 0.1  # 연결당 move 최대 10/s
EMOTE_INTERVAL = 1.0


async def _drain(websocket: WebSocket, q: asyncio.Queue[str]) -> None:
    while True:
        await websocket.send_text(await q.get())


@router.websocket("/{community_id}/space/ws")
async def space_ws(websocket: WebSocket, community_id: uuid.UUID, token: str) -> None:
    # 브라우저 WebSocket은 Authorization 헤더를 못 붙여서 토큰을 쿼리로 받는다
    try:
        with Session(engine) as session:
            user = get_current_user(session, token)
            # 커뮤니티에 입장(POST /communities/{id}/join)한 사람만 공간에 들어온다
            if session.get(CommunityMember, (community_id, user.id)) is None:
                raise HTTPException(status_code=404)
            uid = str(user.id)
            me: dict[str, Any] = {
                "user_id": uid,
                "name": user.display_nickname,
                "avatar_url": user.profile_image_url,
                "x": random.randrange(W),
                "y": random.randrange(H),
            }
    except HTTPException:
        await websocket.close(code=1008)
        return

    cid = str(community_id)
    await hub.start()
    await websocket.accept()
    # 먼저 큐를 걸어 두고 snapshot을 만든다: 그 사이 이벤트도 큐에 남는다(받는 쪽은 덮어쓰기라 겹쳐도 된다)
    q = hub.register(cid)
    sender: asyncio.Task[None] | None = None
    try:
        me = await hub.join(cid, me)
        await websocket.send_json(
            {
                "type": "snapshot",
                "v": 1,
                "me": uid,
                "room": {"id": cid, "w": W, "h": H},
                "users": await hub.snapshot(cid),
                "chat": await hub.chat_history(cid),
            }
        )
        sender = asyncio.create_task(_drain(websocket, q))
        last_move = last_emote = 0.0
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                kind = msg["type"]
                now = time.monotonic()
                if kind == "move":
                    if now - last_move < MOVE_INTERVAL:
                        continue
                    last_move = now
                    x = min(max(int(msg["x"]), 0), W - 1)
                    y = min(max(int(msg["y"]), 0), H - 1)
                    await hub.move(cid, uid, x, y)
                elif kind == "emote" and msg["emote"] in EMOTES:
                    if now - last_emote < EMOTE_INTERVAL:
                        continue
                    last_emote = now
                    await hub.emote(cid, uid, msg["emote"])
                elif kind == "chat":
                    text = str(msg["text"]).strip()[:CHAT_TEXT_MAX]
                    if text:
                        await hub.chat(cid, me, text)
                elif kind == "ping":
                    await hub.touch(cid, uid)
                    q.put_nowait('{"type":"pong"}')
                else:
                    raise ValueError(kind)
            except ValueError, KeyError, TypeError:
                q.put_nowait(json.dumps({"type": "error", "code": "bad_message"}))
    except WebSocketDisconnect:
        pass
    finally:
        if sender is not None:
            sender.cancel()
        hub.unregister(cid, q)
        # 연결이 끊기며 이 코루틴이 취소돼도 접속 수 감소와 leave 발행은 끝까지 하게 한다
        await asyncio.shield(hub.leave(cid, uid))
