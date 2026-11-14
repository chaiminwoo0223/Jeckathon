import uuid

import pytest
import redis
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from starlette.websockets import WebSocketDisconnect

from app.api.routes.communities import get_or_create_community
from app.core.config import settings
from app.models import Match


def _url(cid: object, headers: dict[str, str]) -> str:
    token = headers["Authorization"].removeprefix("Bearer ")
    return f"{settings.API_V1_STR}/communities/{cid}/space/ws?token={token}"


def test_space_join_move_leave(
    client: TestClient,
    db: Session,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    match = db.exec(select(Match)).first()
    assert match is not None
    cid = get_or_create_community(db, match.id).id
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
            # 범위 밖 좌표는 방 안으로 잘린다
            a.send_json({"type": "move", "x": 99, "y": -5})
            want = {"type": "move", "user_id": a_id, "x": 19, "y": 0}
            while (msg := b.receive_json())["type"] != "move":
                pass
            assert msg == want
            b_id = snap_b["me"]
        while (msg := a.receive_json())["type"] != "leave":
            pass
        assert msg == {"type": "leave", "user_id": b_id}


def test_space_rejects_bad_token_and_unknown_community(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    for url in (
        f"{settings.API_V1_STR}/communities/{uuid.uuid4()}/space/ws?token=bad",
        _url(uuid.uuid4(), normal_user_token_headers),
    ):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(url) as ws:
                ws.receive_json()
