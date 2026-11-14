# ruff: noqa: T201, B905, B023  - CLI 스크립트(print), 짝 맞춘 zip, while 안에서 바로 쓰는 lambda
"""채팅 스모크: 계정 생성 -> 경기 응원 선택 -> 커뮤니티 입장 -> 공간 WS 채팅.

두 사용자가 오늘 경기의 홈/원정 팀을 하나씩 응원하고 같은 커뮤니티에 들어가
서로의 채팅을 받는지 본다.

    uv run python scripts/smoke_chat.py [BASE_URL]   # 기본 http://localhost:8000

주의: 대상 서버에 smoke_* 계정 2개와 응원 기록이 남는다.
"""

import asyncio
import json
import secrets
import sys

import httpx
import websockets

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
API = f"{BASE}/api/v1"
WS = API.replace("http", "ws", 1)


def step(name: str, r: httpx.Response) -> dict:
    ok = r.status_code < 300
    print(f"[{'OK' if ok else 'FAIL'}] {name}: {r.status_code}")
    if not ok:
        sys.exit(f"  {r.text[:300]}")
    return r.json()


def setup_user(c: httpx.Client, match: dict, team: dict) -> tuple[str, str]:
    name = f"smoke_{secrets.token_hex(4)}"
    token = step(
        f"{name} signup",
        c.post(f"{API}/auth/signup", json={"username": name, "password": "smoke1234"}),
    )["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    step(
        f"{name} cheer {team['name']}",
        c.post(
            f"{API}/matches/{match['id']}/cheer",
            json={"cheered_team_id": team["id"]},
            headers=h,
        ),
    )
    info = step(
        f"{name} community", c.get(f"{API}/matches/{match['id']}/community", headers=h)
    )
    step(f"{name} join", c.post(f"{API}/communities/{info['id']}/join", headers=h))
    return token, info["id"]


async def recv_until(ws, pred, timeout=5.0) -> dict:
    async def loop():
        while True:
            m = json.loads(await ws.recv())
            if pred(m):
                return m

    return await asyncio.wait_for(loop(), timeout)


async def chat(users: list[tuple[str, str, str]]) -> None:
    url = lambda cid, t: f"{WS}/space/{cid}/ws?token={t}"  # noqa: E731
    async with (
        websockets.connect(url(users[0][1], users[0][0])) as a,
        websockets.connect(url(users[1][1], users[1][0])) as b,
    ):
        for ws, (_, _, team) in zip((a, b), users):
            snap = await recv_until(ws, lambda m: m["type"] == "snapshot")
            print(f"[OK] {team} snapshot: users={len(snap['users'])}")
        texts = [f"{team} 화이팅 {secrets.token_hex(2)}" for _, _, team in users]
        for ws, text in zip((a, b), texts):
            await ws.send(json.dumps({"type": "chat", "text": text}))
        for ws, (_, _, team) in zip((a, b), users):
            want = set(texts)  # 도착 순서는 워커마다 다를 수 있다
            while want:
                m = await recv_until(
                    ws, lambda m: m["type"] == "chat" and m["text"] in want
                )
                want.discard(m["text"])
                print(f"[OK] {team} got chat from {m['name']}: {m['text']}")


def main() -> None:
    with httpx.Client(timeout=10) as c:
        matches = step("matches/today", c.get(f"{API}/matches/today"))["data"]
        live = [m for m in matches if m["status"] != "FINISHED"]
        if not live:
            sys.exit("오늘 끝나지 않은 경기가 없음")
        match = live[0]
        print(f"match: {match['home_team']['name']} vs {match['away_team']['name']}")
        users = []
        for team in (match["home_team"], match["away_team"]):
            token, cid = setup_user(c, match, team)
            users.append((token, cid, team["name"]))
    assert users[0][1] == users[1][1], "두 팀이 다른 커뮤니티"
    asyncio.run(chat(users))
    print("PASS")


if __name__ == "__main__":
    main()
