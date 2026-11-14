import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings

WS = f"{settings.API_V1_STR}/chat/rooms"


def test_chat_broadcasts_within_room_only(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    token = normal_user_token_headers["Authorization"].removeprefix("Bearer ")
    with (
        client.websocket_connect(f"{WS}/1/ws?token={token}") as a,
        client.websocket_connect(f"{WS}/1/ws?token={token}") as b,
        client.websocket_connect(f"{WS}/2/ws?token={token}") as c,
    ):
        a.send_text("hello room 1")
        assert a.receive_json()["text"] == "hello room 1"
        assert b.receive_json()["text"] == "hello room 1"
        # 방 2는 방 1 메시지를 받지 않으므로 다음에 받는 건 자기 메시지다
        c.send_text("hello room 2")
        msg = c.receive_json()
        assert (msg["room_id"], msg["text"]) == (2, "hello room 2")


def test_chat_rejects_bad_token_and_unknown_room(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    token = normal_user_token_headers["Authorization"].removeprefix("Bearer ")
    for url in (f"{WS}/1/ws?token=bad", f"{WS}/3/ws?token={token}"):
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(url) as ws:
                ws.receive_json()
