"""커뮤니티 공간(메타버스): 누가 있고 어디 서 있는지를 Redis에 두고, 워커 사이는 Redis pub/sub으로 퍼뜨린다.

`fastapi run --workers 4`라 WebSocket 연결이 워커마다 흩어진다. 상태는 모든 워커가 같이 보는
Redis에 두고, 이벤트는 커뮤니티마다 채널 하나(`space:{cid}`)로 보낸다. 워커는 `space:*`를
한 번만 구독해서 자기에게 붙은 연결에만 넘긴다.

키 (cid = Community.id):
- space:{cid}:users  HASH  user_id -> {"user_id","nickname","team","x","z","r"} JSON
- space:{cid}:seen   ZSET  user_id -> 마지막 활동 시각(epoch 초). SEEN_TTL 지나면 snapshot 때 지운다
- space:{cid}:conns  HASH  user_id -> 열린 연결 수(탭 여러 개). 0이 되면 leave
- space:{cid}:chat   LIST  최근 채팅 CHAT_KEEP개(JSON)
"""

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

# 원형 경기장 중심(0,0)에서 움직일 수 있는 반경. 프론트 ARENA_PLAY_RADIUS(18 - 1.5)와 같게 둔다
RADIUS = 16.5
SEEN_TTL = 60  # 초. 클라이언트는 25초마다 ping을 보낸다
KEY_TTL = 86400  # 아무도 안 오는 방의 키는 하루 뒤 사라진다
QUEUE_MAX = 256
CHAT_KEEP = 50  # 방마다 최근 채팅만 Redis LIST(space:{cid}:chat)에 둔다
CHAT_TEXT_MAX = 500
TICK = 0.1  # 초. move를 모아 보내는 간격(연결당 최대 10프레임/s)

logger = logging.getLogger(__name__)


def _key(cid: str, name: str) -> str:
    return f"space:{cid}:{name}"


def _dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False)


class Hub:
    def __init__(self) -> None:
        self.rooms: dict[str, set[asyncio.Queue[str]]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._r: redis.Redis | None = None
        self._listener: asyncio.Task[None] | None = None
        self._flusher: asyncio.Task[None] | None = None
        self._ready: asyncio.Event | None = None
        # cid -> user_id -> [x, z, r]: 이번 TICK에 모인 마지막 위치
        self.pending: dict[str, dict[str, list[float]]] = {}

    @property
    def r(self) -> redis.Redis:
        assert self._r is not None
        return self._r

    async def start(self) -> None:
        """구독이 걸릴 때까지 기다린다. 첫 접속 때 실행 중인 이벤트 루프에서 띄운다."""
        loop = asyncio.get_running_loop()
        if self._loop is not loop or self._listener is None or self._listener.done():
            # redis 연결은 만든 루프에 묶이므로 루프가 바뀌면 새로 만든다
            self._loop = loop
            self._r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self._ready = asyncio.Event()
            self.pending = {}
            self._listener = asyncio.create_task(self._listen())
            self._flusher = asyncio.create_task(self._flush())
        assert self._ready is not None
        await asyncio.wait_for(self._ready.wait(), timeout=5)

    async def _listen(self) -> None:
        # shortcut: 재접속 사이(약 1초) 이벤트는 잃는다. 위치는 다음 move나 재접속 snapshot으로 맞춰진다.
        while True:
            try:
                async with self.r.pubsub() as ps:
                    await ps.psubscribe("space:*")
                    assert self._ready is not None
                    self._ready.set()
                    async for m in ps.listen():
                        if m["type"] == "pmessage":
                            self._fanout(m["channel"].removeprefix("space:"), m["data"])
            except Exception:
                logger.exception("space listener disconnected, retrying in 1s")
                await asyncio.sleep(1)

    def _fanout(self, cid: str, data: str) -> None:
        if cid not in self.rooms:
            return
        msg = json.loads(data)
        if msg["type"] == "move":
            # move는 바로 보내지 않고 사람별 마지막 위치만 모아 TICK마다 한 프레임으로 보낸다
            self.pending.setdefault(cid, {})[msg["user_id"]] = [
                msg["x"],
                msg["z"],
                msg["r"],
            ]
            return
        if msg["type"] == "leave":
            self.pending.get(cid, {}).pop(msg["user_id"], None)
        self._put(cid, data)

    async def _flush(self) -> None:
        while True:
            await asyncio.sleep(TICK)
            pending, self.pending = self.pending, {}
            for cid, moves in pending.items():
                self._put(cid, _dumps({"type": "moves", "p": moves}))

    def _put(self, cid: str, data: str) -> None:
        for q in list(self.rooms.get(cid, ())):
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                # 받는 쪽이 못 따라오면 버린다. 다음 move가 최신 위치를 다시 준다
                pass

    def register(self, cid: str) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue(maxsize=QUEUE_MAX)
        self.rooms.setdefault(cid, set()).add(q)
        return q

    def unregister(self, cid: str, q: asyncio.Queue[str]) -> None:
        room = self.rooms.get(cid)
        if room is not None:
            room.discard(q)
            if not room:
                del self.rooms[cid]

    async def join(self, cid: str, user: dict[str, Any]) -> dict[str, Any]:
        """같은 사람이 이미 있으면(다른 탭) 그 자리를 이어 쓴다."""
        uid = user["user_id"]
        old = await self.r.hget(_key(cid, "users"), uid)
        if old:
            prev = json.loads(old)
            user = {**user, "x": prev["x"], "z": prev["z"], "r": prev["r"]}
        async with self.r.pipeline(transaction=True) as p:
            p.hset(_key(cid, "users"), uid, _dumps(user))
            p.zadd(_key(cid, "seen"), {uid: time.time()})
            p.hincrby(_key(cid, "conns"), uid, 1)
            for name in ("users", "seen", "conns"):
                p.expire(_key(cid, name), KEY_TTL)
            p.publish(f"space:{cid}", _dumps({"type": "join", "user": user}))
            await p.execute()
        return user

    async def snapshot(self, cid: str) -> list[dict[str, Any]]:
        # 스케줄러 없이 조회할 때 오래 조용한 사람(워커가 죽어 leave를 못 보낸 경우)을 지운다
        stale = await self.r.zrangebyscore(
            _key(cid, "seen"), "-inf", time.time() - SEEN_TTL
        )
        for uid in stale:
            await self._remove(cid, str(uid))
        return [json.loads(u) for u in await self.r.hvals(_key(cid, "users"))]

    async def leave(self, cid: str, uid: str) -> None:
        if await self.r.hincrby(_key(cid, "conns"), uid, -1) <= 0:
            await self._remove(cid, uid)

    async def _remove(self, cid: str, uid: str) -> None:
        async with self.r.pipeline(transaction=True) as p:
            p.hdel(_key(cid, "users"), uid)
            p.hdel(_key(cid, "conns"), uid)
            p.zrem(_key(cid, "seen"), uid)
            p.publish(f"space:{cid}", _dumps({"type": "leave", "user_id": uid}))
            await p.execute()

    async def move(self, cid: str, uid: str, x: float, z: float, r: float) -> None:
        raw = await self.r.hget(_key(cid, "users"), uid)
        if raw is None:  # 오래 조용해서 지워졌다. 재접속하면 다시 생긴다
            return
        user = {**json.loads(raw), "x": x, "z": z, "r": r}
        async with self.r.pipeline(transaction=True) as p:
            p.hset(_key(cid, "users"), uid, _dumps(user))
            p.zadd(_key(cid, "seen"), {uid: time.time()})
            p.publish(
                f"space:{cid}",
                _dumps({"type": "move", "user_id": uid, "x": x, "z": z, "r": r}),
            )
            await p.execute()

    async def emote(self, cid: str, uid: str, emote: str) -> None:
        async with self.r.pipeline(transaction=True) as p:
            p.zadd(_key(cid, "seen"), {uid: time.time()})
            p.publish(
                f"space:{cid}",
                _dumps({"type": "emote", "user_id": uid, "emote": emote}),
            )
            await p.execute()

    async def chat(self, cid: str, user: dict[str, Any], text: str) -> None:
        msg = {
            "type": "chat",
            "user_id": user["user_id"],
            "name": user["nickname"],
            "text": text,
            "sent_at": datetime.now(UTC).isoformat(),
        }
        data = _dumps(msg)
        # 기록과 발행을 한 트랜잭션으로: Redis가 워커 사이 순서를 하나로 정하고, 기록도 그 순서다
        async with self.r.pipeline(transaction=True) as p:
            p.rpush(_key(cid, "chat"), data)
            p.ltrim(_key(cid, "chat"), -CHAT_KEEP, -1)
            p.expire(_key(cid, "chat"), KEY_TTL)
            p.zadd(_key(cid, "seen"), {user["user_id"]: time.time()})
            p.publish(f"space:{cid}", data)
            await p.execute()

    async def chat_history(self, cid: str) -> list[dict[str, Any]]:
        return [json.loads(m) for m in await self.r.lrange(_key(cid, "chat"), 0, -1)]

    async def say(self, cid: str, uid: str, text: str) -> None:
        """머리 위 말풍선. 저장하지 않는다(대화 기록은 채팅 WS)."""
        async with self.r.pipeline(transaction=True) as p:
            p.zadd(_key(cid, "seen"), {uid: time.time()})
            p.publish(
                f"space:{cid}", _dumps({"type": "say", "user_id": uid, "text": text})
            )
            await p.execute()

    async def touch(self, cid: str, uid: str) -> None:
        await self.r.zadd(_key(cid, "seen"), {uid: time.time()})


hub = Hub()
