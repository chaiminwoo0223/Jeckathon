import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, select

from app.core.config import settings
from app.models import CheerRecord, CheerResult, Match, MatchStatus, Team

API = settings.API_V1_STR

_created_matches: list[uuid.UUID] = []


@pytest.fixture(scope="module", autouse=True)
def _cleanup_matches(db: Session) -> Generator[None]:
    """이 파일이 만든 경기만 지운다(응원 기록은 FK cascade)."""
    yield
    if _created_matches:
        db.execute(delete(Match).where(col(Match.id).in_(_created_matches)))
        db.commit()


class Fan:
    def __init__(self, client: TestClient) -> None:
        name = f"u{uuid.uuid4().hex[:12]}"
        r = client.post(
            f"{API}/auth/signup", json={"username": name, "password": "pw1234"}
        )
        self.client = client
        self.name = name
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        self.id = uuid.UUID(r.json()["user"]["id"])

    def card(self) -> dict:
        r = self.client.get(f"{API}/me/share-card", headers=self.headers)
        assert r.status_code == 200, r.text
        return r.json()


def _teams(db: Session, n: int = 3) -> list[Team]:
    return list(db.exec(select(Team).limit(n)).all())


def _record(
    db: Session,
    fan: Fan,
    team: Team,
    other: Team,
    result: CheerResult,
    cheered_at: datetime,
    days: int = 90,
) -> None:
    match = Match(
        home_team_id=team.id,
        away_team_id=other.id,
        league="KBO리그",
        kickoff_at=datetime.now(UTC) + timedelta(days=days),
        status=MatchStatus.SCHEDULED,
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    _created_matches.append(match.id)
    db.add(
        CheerRecord(
            user_id=fan.id,
            match_id=match.id,
            cheered_team_id=team.id,
            result=result,
            created_at=cheered_at,
        )
    )
    db.commit()


def test_share_card_requires_auth(client: TestClient) -> None:
    assert client.get(f"{API}/me/share-card").status_code == 401


def test_share_card_for_new_user(client: TestClient) -> None:
    fan = Fan(client)
    card = fan.card()
    assert card["nickname"] == fan.name
    assert card["profile_image_url"] is None
    assert card["fairy_type"] == "NEUTRAL"
    assert card["fairy_label"] == f"중립요정 {fan.name}"
    assert card["stats"] == {
        "total": 0,
        "win": 0,
        "draw": 0,
        "lose": 0,
        "win_rate": 0.0,
        "lose_rate": 0.0,
    }
    assert card["favorite_team"] is None


def test_share_card_uses_profile(client: TestClient) -> None:
    fan = Fan(client)
    client.patch(
        f"{API}/me/profile",
        headers=fan.headers,
        json={"nickname": "뚜비응원단", "profile_image_url": "https://img.test/a.png"},
    )
    card = fan.card()
    assert card["nickname"] == "뚜비응원단"
    assert card["profile_image_url"] == "https://img.test/a.png"
    assert card["fairy_label"] == "중립요정 뚜비응원단"


def test_favorite_team_falls_back_to_my_teams(client: TestClient, db: Session) -> None:
    fan = Fan(client)
    a, b, _ = _teams(db)
    for t in (a, b):
        client.post(f"{API}/me/teams", headers=fan.headers, json={"team_id": str(t.id)})
    first = client.get(f"{API}/me/teams", headers=fan.headers).json()["data"][0]
    # 응원 기록이 없으면 응원팀 설정의 첫 팀(/me/teams와 같은 정렬)
    assert fan.card()["favorite_team"]["id"] == first["id"]


def test_favorite_team_is_most_cheered_and_beats_my_teams(
    client: TestClient, db: Session
) -> None:
    fan = Fan(client)
    a, b, c = _teams(db)
    client.post(f"{API}/me/teams", headers=fan.headers, json={"team_id": str(c.id)})
    now = datetime.now(UTC)
    _record(db, fan, a, c, CheerResult.PENDING, now - timedelta(days=3), days=91)
    _record(db, fan, b, c, CheerResult.PENDING, now - timedelta(days=2), days=92)
    _record(db, fan, a, c, CheerResult.PENDING, now - timedelta(days=1), days=93)
    team = fan.card()["favorite_team"]
    assert team["id"] == str(a.id)  # a 2회 > b 1회, 응원팀 설정(c)보다 기록이 우선
    assert {"name", "full_name", "logo_url", "league"} <= set(team)


def test_favorite_team_tie_goes_to_most_recent(client: TestClient, db: Session) -> None:
    fan = Fan(client)
    a, b, c = _teams(db)
    now = datetime.now(UTC)
    _record(db, fan, a, c, CheerResult.PENDING, now - timedelta(days=5), days=94)
    _record(db, fan, b, c, CheerResult.PENDING, now - timedelta(days=1), days=95)
    assert fan.card()["favorite_team"]["id"] == str(b.id)  # 1회씩이면 더 최근
    _record(db, fan, a, c, CheerResult.PENDING, now - timedelta(days=9), days=96)
    assert fan.card()["favorite_team"]["id"] == str(a.id)  # 이제 a가 2회


def test_favorite_team_ignores_other_users(client: TestClient, db: Session) -> None:
    mine, other = Fan(client), Fan(client)
    a, b, c = _teams(db)
    now = datetime.now(UTC)
    _record(db, mine, b, c, CheerResult.PENDING, now, days=97)
    for d in (98, 99):
        _record(db, other, a, c, CheerResult.PENDING, now, days=d)
    assert mine.card()["favorite_team"]["id"] == str(b.id)


def test_share_card_stats_and_fairy_match_me(client: TestClient, db: Session) -> None:
    fan = Fan(client)
    a, _, c = _teams(db)
    now = datetime.now(UTC)
    # 승2 무1 패1 + 진행 전 1건: 경기수·승률은 확정된 기록만
    for i, result in enumerate(
        (
            CheerResult.WIN,
            CheerResult.WIN,
            CheerResult.DRAW,
            CheerResult.LOSE,
            CheerResult.PENDING,
        )
    ):
        _record(db, fan, a, c, result, now - timedelta(hours=i), days=100 + i)
    card = fan.card()
    me = client.get(f"{API}/me", headers=fan.headers).json()
    assert card["stats"] == me["stats"]
    assert card["stats"]["total"] == 4
    assert card["stats"]["win_rate"] == 0.67
    assert (card["fairy_type"], card["fairy_label"]) == (
        me["fairy_type"],
        me["fairy_label"],
    )
    assert card["fairy_type"] == "VICTORY"
    assert card["favorite_team"]["id"] == str(a.id)  # 진행 전 기록도 응원으로 센다
