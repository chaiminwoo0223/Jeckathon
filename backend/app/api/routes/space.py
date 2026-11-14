import asyncio
import json
import math
import random
import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.db import engine
from app.models import CheerRecord, Community, CommunityMember, Team
from app.services.space import CHAT_TEXT_MAX, RADIUS, hub

router = APIRouter(prefix="/space", tags=["space"])

EMOTES = {"clap", "cheer", "wave", "fire"}
MOVE_INTERVAL = 0.1  # 연결당 위치 반영 최대 10/s. 더 자주 오면 마지막 값만 쓴다
EMOTE_INTERVAL = 1.0
SAY_INTERVAL = 1.0
SAY_MAX = 60


def _num(v: Any) -> float:
    f = float(v)
    if not math.isfinite(f):
        raise ValueError(v)
    return f


def _clamp(x: float, z: float) -> tuple[float, float]:
    d = math.hypot(x, z)
    if d <= RADIUS:
        return x, z
    return x * RADIUS / d, z * RADIUS / d


async def _drain(websocket: WebSocket, q: asyncio.Queue[str]) -> None:
    while True:
        await websocket.send_text(await q.get())


@router.websocket("/{community_id}/ws")
async def space_ws(websocket: WebSocket, community_id: uuid.UUID, token: str) -> None:
    # 브라우저 WebSocket은 Authorization 헤더를 못 붙여서 토큰을 쿼리로 받는다
    try:
        with Session(engine) as session:
            user = get_current_user(session, token)
            community = session.get(Community, community_id)
            # 커뮤니티에 입장(POST /communities/{id}/join)한 사람만 공간에 들어온다
            if (
                community is None
                or session.get(CommunityMember, (community_id, user.id)) is None
            ):
                raise HTTPException(status_code=404)
            # 유니폼: 이 경기에서 고른 응원팀
            record = session.exec(
                select(CheerRecord).where(
                    CheerRecord.user_id == user.id,
                    CheerRecord.match_id == community.match_id,
                )
            ).first()
            team = session.get(Team, record.cheered_team_id) if record else None
            uid = str(user.id)
            a, d = random.uniform(0, 2 * math.pi), RADIUS * math.sqrt(random.random())
            me: dict[str, Any] = {
                "user_id": uid,
                "nickname": user.display_nickname,
                "team": {"name": team.name, "color": team.color} if team else None,
                "x": round(d * math.cos(a), 2),
                "z": round(d * math.sin(a), 2),
                "r": 0.0,
            }
    except HTTPException:
        # accept 전에 닫으면 브라우저는 1006만 본다. 받고 닫아야 1008(재연결 금지 신호)이 간다
        await websocket.accept()
        await websocket.close(code=1008)
        return

    cid = str(community_id)
    await hub.start()
    await websocket.accept()
    # 먼저 큐를 걸어 두고 snapshot을 만든다: 그 사이 이벤트도 큐에 남는다(받는 쪽은 덮어쓰기라 겹쳐도 된다)
    q = hub.register(cid)
    tasks: list[asyncio.Task[None]] = []
    # 클라이언트가 매 프레임 move를 보내도 0.1초마다 마지막 값 하나만 반영한다(멈춘 자리도 빠지지 않는다)
    pending: dict[str, tuple[float, float, float]] = {}

    async def _mover() -> None:
        while True:
            await asyncio.sleep(MOVE_INTERVAL)
            if pos := pending.pop("me", None):
                await hub.move(cid, uid, *pos)

    try:
        me = await hub.join(cid, me)
        await websocket.send_json(
            {
                "type": "snapshot",
                "v": 2,
                "me": uid,
                "room": {"id": cid, "radius": RADIUS},
                "users": await hub.snapshot(cid),
                "chat": await hub.chat_history(cid),
            }
        )
        tasks = [
            asyncio.create_task(_drain(websocket, q)),
            asyncio.create_task(_mover()),
        ]
        last_emote = last_say = 0.0
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                kind = msg["type"]
                now = time.monotonic()
                if kind == "move":
                    x, z = _clamp(_num(msg["x"]), _num(msg["z"]))
                    r = _num(msg.get("r", 0)) % (2 * math.pi)
                    pending["me"] = (round(x, 2), round(z, 2), round(r, 2))
                elif kind == "emote" and msg["emote"] in EMOTES:
                    if now - last_emote < EMOTE_INTERVAL:
                        continue
                    last_emote = now
                    await hub.emote(cid, uid, msg["emote"])
                elif kind == "chat":
                    text = str(msg["text"]).strip()[:CHAT_TEXT_MAX]
                    if text:
                        await hub.chat(cid, me, text)
                elif kind == "say":
                    text = str(msg["text"]).strip()[:SAY_MAX]
                    if not text or now - last_say < SAY_INTERVAL:
                        continue
                    last_say = now
                    await hub.say(cid, uid, text)
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
        for t in tasks:
            t.cancel()
        hub.unregister(cid, q)
        # 연결이 끊기며 이 코루틴이 취소돼도 접속 수 감소와 leave 발행은 끝까지 하게 한다
        await asyncio.shield(hub.leave(cid, uid))
