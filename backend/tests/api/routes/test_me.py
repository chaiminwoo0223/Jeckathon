import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import Team, User
from app.services import stats

API = settings.API_V1_STR


def _team_id(db: Session, name: str) -> str:
    team = db.exec(select(Team).where(Team.name == name)).one()
    return str(team.id)


# --- 승률·요정 판정 (명세 §3.1, §3.2) ---


def test_rates_exclude_draws() -> None:
    assert stats.rates(28, 13) == (28 / 41, 13 / 41)
    assert stats.rates(0, 0) == (0.0, 0.0)


def test_build_stats_matches_spec_example() -> None:
    s = stats.build_stats(win=28, draw=3, lose=13)
    assert (s.total, s.win, s.draw, s.lose) == (44, 28, 3, 13)
    assert (s.win_rate, s.lose_rate) == (0.68, 0.32)


def test_fairy_type_rules() -> None:
    assert stats.fairy_type(28, 13).value == "VICTORY"  # 68%
    assert stats.fairy_type(6, 4).value == "VICTORY"  # 승률 경계 60%
    assert stats.fairy_type(7, 3).value == "VICTORY"  # 패배율 30%여도 승리요정 우선
    assert stats.fairy_type(5, 5).value == "DEFEAT"  # 승률 50% < 60%, 패배율 50% >= 30%
    assert stats.fairy_type(1, 9).value == "DEFEAT"
    assert stats.fairy_type(0, 0).value == "NEUTRAL"  # 기록 없음
    assert stats.fairy_label(stats.fairy_type(28, 13), "뚜비") == "승리요정 뚜비"


# --- /me ---


def test_me_requires_auth(client: TestClient) -> None:
    for method, path in [
        ("get", "/me"),
        ("patch", "/me/profile"),
        ("get", "/me/settings"),
        ("get", "/me/teams"),
    ]:
        assert client.request(method, f"{API}{path}").status_code == 401


def test_read_me_defaults(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{API}/me", headers=normal_user_token_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["fairy_type"] == "NEUTRAL"
    assert body["fairy_label"] == f"중립요정 {body['nickname']}"
    assert body["nickname"]  # 닉네임이 비어 있어도 이메일 앞부분으로 채워진다
    assert body["stats"] == {
        "total": 0,
        "win": 0,
        "draw": 0,
        "lose": 0,
        "win_rate": 0.0,
        "lose_rate": 0.0,
    }
    assert body["level"] == 1
    assert body["total_points"] == 0
    assert isinstance(body["teams"], list)


def test_update_profile(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = client.patch(
        f"{API}/me/profile",
        headers=normal_user_token_headers,
        json={"nickname": "뚜비응원단", "bio": "LG 광팬"},
    )
    assert r.status_code == 200
    assert (r.json()["nickname"], r.json()["bio"]) == ("뚜비응원단", "LG 광팬")

    # 일부만 보내면 나머지는 유지, nickname null은 변경 없음
    r = client.patch(
        f"{API}/me/profile",
        headers=normal_user_token_headers,
        json={"nickname": None, "profile_image_url": "https://img.test/a.png"},
    )
    assert r.json()["nickname"] == "뚜비응원단"
    assert r.json()["bio"] == "LG 광팬"
    assert r.json()["profile_image_url"] == "https://img.test/a.png"

    me = client.get(f"{API}/me", headers=normal_user_token_headers).json()
    assert me["fairy_label"] == "중립요정 뚜비응원단"

    # 이미지 URL은 null로 지울 수 있다
    r = client.patch(
        f"{API}/me/profile",
        headers=normal_user_token_headers,
        json={"profile_image_url": None},
    )
    assert r.json()["profile_image_url"] is None

    r = client.patch(
        f"{API}/me/profile", headers=normal_user_token_headers, json={"nickname": ""}
    )
    assert r.status_code == 422


def test_settings_defaults_and_patch(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    r = client.get(f"{API}/me/settings", headers=normal_user_token_headers)
    assert r.status_code == 200
    assert r.json() == {
        "notify_match_schedule": True,
        "notify_community_invite": True,
        "notify_ranking_reward": True,
        "notify_service": False,
        "auto_join_community": True,
        "mic_permission": False,
        "ranking_public": True,
    }

    r = client.patch(
        f"{API}/me/settings",
        headers=normal_user_token_headers,
        json={"mic_permission": True, "ranking_public": False},
    )
    assert r.status_code == 200
    assert r.json()["mic_permission"] is True
    again = client.get(f"{API}/me/settings", headers=normal_user_token_headers).json()
    assert again["mic_permission"] is True
    assert again["ranking_public"] is False
    assert again["notify_service"] is False  # 보내지 않은 값은 그대로


def test_my_teams_add_list_remove(
    client: TestClient,
    db: Session,
    normal_user_token_headers: dict[str, str],
) -> None:
    lg, doosan = _team_id(db, "LG"), _team_id(db, "두산")
    h = normal_user_token_headers
    # 이전 테스트 잔여물 정리
    for t in client.get(f"{API}/me/teams", headers=h).json()["data"]:
        client.delete(f"{API}/me/teams/{t['id']}", headers=h)

    assert client.get(f"{API}/me/teams", headers=h).json() == {"data": [], "count": 0}

    r = client.post(f"{API}/me/teams", headers=h, json={"team_id": lg})
    assert r.status_code == 200
    assert [t["name"] for t in r.json()["data"]] == ["LG"]

    # 중복 추가는 그대로 둔다
    r = client.post(f"{API}/me/teams", headers=h, json={"team_id": lg})
    assert r.json()["count"] == 1

    client.post(f"{API}/me/teams", headers=h, json={"team_id": doosan})
    me = client.get(f"{API}/me", headers=h).json()
    assert {t["name"] for t in me["teams"]} == {"LG", "두산"}

    r = client.delete(f"{API}/me/teams/{lg}", headers=h)
    assert r.status_code == 200
    assert [t["name"] for t in r.json()["data"]] == ["두산"]

    assert client.delete(f"{API}/me/teams/{lg}", headers=h).status_code == 404
    r = client.post(f"{API}/me/teams", headers=h, json={"team_id": str(uuid.uuid4())})
    assert r.status_code == 404


def test_teams_are_per_user(client: TestClient, db: Session) -> None:
    lg = _team_id(db, "LG")

    def signup() -> dict[str, str]:
        name = f"u{uuid.uuid4().hex[:12]}"
        r = client.post(
            f"{API}/auth/signup", json={"username": name, "password": "pw1234"}
        )
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    a, b = signup(), signup()
    client.post(f"{API}/me/teams", headers=a, json={"team_id": lg})
    assert client.get(f"{API}/me/teams", headers=a).json()["count"] == 1
    assert client.get(f"{API}/me/teams", headers=b).json()["count"] == 0


def test_display_nickname_fallback() -> None:
    user = User(email="fan@example.com", hashed_password="x")
    assert user.display_nickname == "fan"  # 닉네임이 비면 이메일 앞부분
    user.nickname = "뚜비"
    assert user.display_nickname == "뚜비"
