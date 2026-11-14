import uuid

import pytest
import redis
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from starlette.websockets import WebSocketDisconnect

from app.api.routes.communities import get_or_create_community
from app.core.config import settings
from app.models import CommunityMember, Match, User


def _url(cid: object, headers: dict[str, str]) -> str:
    token = headers["Authorization"].removeprefix("Bearer ")
    return f"{settings.API_V1_STR}/space/{cid}/ws?token={token}"


def test_space_join_move_leave(
    client: TestClient,
    db: Session,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    match = db.exec(select(Match)).first()
    assert match is not None
    cid = get_or_create_community(db, match.id).id
    for email in (settings.EMAIL_TEST_USER, settings.FIRST_SUPERUSER):
        user = db.exec(select(User).where(User.email == email)).one()
        if db.get(CommunityMember, (cid, user.id)) is None:
            db.add(CommunityMember(community_id=cid, user_id=user.id))
    db.commit()
    # 앞선 실행이 남긴 접속 수가 있으면 leave가 안 온다
    redis.Redis.from_url(settings.REDIS_URL).delete(
        *(f"space:{cid}:{k}" for k in ("users", "seen", "conns"))
    )

    with client.websocket_connect(_url(cid, normal_user_token_headers)) as a:
        snap_a = a.receive_json()
        assert snap_a["type"] == "snapshot"
        a_id = snap_a["me"]
        assert a_id in [u["user_id"] for u in snap_a["users"]]
        assert a.receive_json()["type"] == "join"  # 자기 입장도 돌아온다

        with client.websocket_connect(_url(cid, superuser_token_headers)) as b:
            snap_b = b.receive_json()
            assert a_id in [u["user_id"] for u in snap_b["users"]]
            # 앞선 실행의 남은 사람이 정리되며 leave가 먼저 올 수 있다
            while (msg := a.receive_json())["type"] != "join":
                pass
            assert msg["user"] == next(
                u for u in snap_b["users"] if u["user_id"] == snap_b["me"]
            )
            # 원 밖 좌표는 경기장 가장자리(반경 16.5)로 잘린다
            a.send_json({"type": "move", "x": 99, "z": 0, "r": 0})
            # move는 TICK마다 사람별 마지막 위치를 모은 moves 프레임으로 온다
            while (msg := b.receive_json())["type"] != "moves":
                pass
            assert msg == {"type": "moves", "p": {a_id: [16.5, 0.0, 0.0]}}
            a.send_json({"type": "say", "text": "  가자!  "})
            while (msg := b.receive_json())["type"] != "say":
                pass
            assert msg == {"type": "say", "user_id": a_id, "text": "가자!"}
            b_id = snap_b["me"]
        while (msg := a.receive_json())["type"] != "leave":
            pass
        assert msg == {"type": "leave", "user_id": b_id}


def test_space_chat_same_order_for_everyone_and_history(
    client: TestClient,
    db: Session,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    match = db.exec(select(Match)).first()
    assert match is not None
    cid = get_or_create_community(db, match.id).id
    for email in (settings.EMAIL_TEST_USER, settings.FIRST_SUPERUSER):
        user = db.exec(select(User).where(User.email == email)).one()
        if db.get(CommunityMember, (cid, user.id)) is None:
            db.add(CommunityMember(community_id=cid, user_id=user.id))
    db.commit()
    redis.Redis.from_url(settings.REDIS_URL).delete(f"space:{cid}:chat")

    def chats(ws: object, n: int) -> list[str]:
        got: list[str] = []
        while len(got) < n:
            msg = ws.receive_json()  # type: ignore[attr-defined]
            if msg["type"] == "chat":
                got.append(msg["text"])
        return got

    with (
        client.websocket_connect(_url(cid, normal_user_token_headers)) as a,
        client.websocket_connect(_url(cid, superuser_token_headers)) as b,
    ):
        assert a.receive_json()["chat"] == []
        b.receive_json()
        sent = []
        for i in range(3):
            for name, ws in (("a", a), ("b", b)):
                sent.append(f"{name}{i}")
                ws.send_json({"type": "chat", "text": f"  {sent[-1]}  "})
        a.send_json({"type": "chat", "text": "   "})  # 빈 글은 버린다
        # 두 사람이 거의 동시에 보내면 서버 도착 순서가 보낸 순서와 다를 수 있다.
        # 지켜야 할 것: 모두 같은 순서로 받고, 한 사람이 보낸 것끼리는 순서가 유지된다
        got = chats(a, 6)
        assert chats(b, 6) == got
        assert sorted(got) == sorted(sent)
        assert [t for t in got if t[0] == "a"] == [t for t in sent if t[0] == "a"]

    # 나중에 들어온 사람은 snapshot의 chat으로 최근 기록을 받는다
    with client.websocket_connect(_url(cid, normal_user_token_headers)) as c:
        assert [m["text"] for m in c.receive_json()["chat"]] == got


def _community_without(db: Session, email: str) -> uuid.UUID:
    """그 사람이 입장하지 않은 커뮤니티 하나."""
    user = db.exec(select(User).where(User.email == email)).one()
    for match in db.exec(select(Match)).all():
        cid = get_or_create_community(db, match.id).id
        if db.get(CommunityMember, (cid, user.id)) is None:
            return cid
    raise AssertionError("no community without membership")


def test_space_rejects_bad_token_unknown_community_and_non_member(
    client: TestClient, db: Session, normal_user_token_headers: dict[str, str]
) -> None:
    for url in (
        f"{settings.API_V1_STR}/space/{uuid.uuid4()}/ws?token=bad",
        _url(uuid.uuid4(), normal_user_token_headers),
        _url(
            _community_without(db, settings.EMAIL_TEST_USER), normal_user_token_headers
        ),
    ):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(url) as ws:
                ws.receive_json()
