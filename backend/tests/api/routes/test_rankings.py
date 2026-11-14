import itertools
import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, select

from app.api.routes.rankings import KST
from app.core.config import settings
from app.models import CheerRecord, CheerResult, Match, MatchStatus, Team

API = settings.API_V1_STR

_created_matches: list[uuid.UUID] = []
_next_day = itertools.count(1000)  # 테스트마다 겹치지 않는 먼 미래 날짜를 쓴다


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


def _new_day() -> date:
    return (datetime.now(KST) + timedelta(days=next(_next_day))).date()


def _match_on(db: Session, day: date, hour: int = 18) -> Match:
    teams = db.exec(select(Team).limit(2)).all()
    match = Match(
        home_team_id=teams[0].id,
        away_team_id=teams[1].id,
        league="KBO리그",
        kickoff_at=datetime(day.year, day.month, day.day, hour, tzinfo=KST).astimezone(
            UTC
        ),
        status=MatchStatus.FINISHED,
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    _created_matches.append(match.id)
    return match


def _record(db: Session, fan: Fan, match: Match, result: CheerResult) -> None:
    db.add(
        CheerRecord(
            user_id=fan.id,
            match_id=match.id,
            cheered_team_id=match.home_team_id,
            result=result,
        )
    )
    db.commit()


def _ranking(client: TestClient, kind: str, day: date, **params: int) -> dict:
    r = client.get(f"{API}/rankings/{kind}", params={"date": day.isoformat(), **params})
    assert r.status_code == 200, r.text
    return r.json()


def test_rankings_are_public_and_empty_for_a_quiet_day(client: TestClient) -> None:
    day = _new_day()
    for kind, fairy in (("victory", "VICTORY"), ("defeat", "DEFEAT")):
        body = _ranking(client, kind, day)
        assert body == {"date": day.isoformat(), "kind": fairy, "data": [], "count": 0}


def test_rankings_default_date_is_today_kst(client: TestClient) -> None:
    r = client.get(f"{API}/rankings/victory")
    assert r.status_code == 200
    assert r.json()["date"] == datetime.now(KST).date().isoformat()


def test_victory_ranking_orders_by_win_rate_then_played(
    client: TestClient, db: Session
) -> None:
    day = _new_day()
    m1, m2, m3 = (_match_on(db, day, h) for h in (12, 15, 18))
    sweep3, sweep1, mixed = Fan(client), Fan(client), Fan(client)
    for m in (m1, m2, m3):
        _record(db, sweep3, m, CheerResult.WIN)  # 3승 → 1.0, 3경기
    _record(db, sweep1, m1, CheerResult.WIN)  # 1승 → 1.0, 1경기
    for m, res in (
        (m1, CheerResult.WIN),
        (m2, CheerResult.WIN),
        (m3, CheerResult.LOSE),
    ):
        _record(db, mixed, m, res)  # 2승1패 → 0.67

    body = _ranking(client, "victory", day)
    assert [e["user_id"] for e in body["data"]] == [
        str(sweep3.id),
        str(sweep1.id),
        str(mixed.id),
    ]
    assert [e["rank"] for e in body["data"]] == [1, 2, 3]
    top = body["data"][0]
    assert top["rate"] == 1.0
    assert (top["played"], top["win"], top["draw"], top["lose"]) == (3, 3, 0, 0)
    assert top["nickname"] == sweep3.name
    assert top["fairy_label"] == f"승리요정 {sweep3.name}"
    assert body["data"][2]["rate"] == 0.67
    assert body["count"] == 3
    # 승리요정이라 패배요정 랭킹에는 오르지 않는다(승리요정 우선)
    assert _ranking(client, "defeat", day)["data"] == []


def test_defeat_ranking_uses_lose_rate_and_excludes_victory_fairies(
    client: TestClient, db: Session
) -> None:
    day = _new_day()
    m1, m2, m3 = (_match_on(db, day, h) for h in (12, 15, 18))
    loser, unlucky, winner = Fan(client), Fan(client), Fan(client)
    for m in (m1, m2):
        _record(db, loser, m, CheerResult.LOSE)  # 2패 → 1.0
    _record(db, unlucky, m1, CheerResult.LOSE)
    _record(db, unlucky, m2, CheerResult.WIN)
    _record(
        db, unlucky, m3, CheerResult.WIN
    )  # 1패 2승 → 패배율 0.33 ≥ 0.3이지만 승률 0.67이라 승리요정
    _record(db, winner, m1, CheerResult.WIN)

    body = _ranking(client, "defeat", day)
    assert [e["user_id"] for e in body["data"]] == [str(loser.id)]
    assert body["data"][0]["rate"] == 1.0
    assert body["data"][0]["fairy_label"] == f"패배요정 {loser.name}"
    victory_ids = {e["user_id"] for e in _ranking(client, "victory", day)["data"]}
    assert victory_ids == {str(unlucky.id), str(winner.id)}


def test_ranking_counts_only_confirmed_records_of_that_kst_day(
    client: TestClient, db: Session
) -> None:
    day = _new_day()
    in_day = _match_on(db, day, 1)  # KST 새벽 1시 = 전날 UTC, 그래도 이 날짜 경기
    next_day = _match_on(db, day + timedelta(days=1), 18)
    fan = Fan(client)
    _record(db, fan, in_day, CheerResult.WIN)
    _record(db, fan, next_day, CheerResult.LOSE)  # 다른 날짜 → 무시
    pending_fan = Fan(client)
    _record(db, pending_fan, in_day, CheerResult.PENDING)  # 미확정 → 무시

    body = _ranking(client, "victory", day)
    assert [e["user_id"] for e in body["data"]] == [str(fan.id)]
    assert body["data"][0]["played"] == 1


def test_ranking_hides_users_with_ranking_public_off(
    client: TestClient, db: Session
) -> None:
    day = _new_day()
    match = _match_on(db, day)
    shown, hidden = Fan(client), Fan(client)
    for fan in (shown, hidden):
        _record(db, fan, match, CheerResult.WIN)
    r = client.patch(
        f"{API}/me/settings", headers=hidden.headers, json={"ranking_public": False}
    )
    assert r.status_code == 200

    body = _ranking(client, "victory", day)
    assert [e["user_id"] for e in body["data"]] == [str(shown.id)]


def test_ranking_limit_and_validation(client: TestClient, db: Session) -> None:
    day = _new_day()
    match = _match_on(db, day)
    for _ in range(3):
        _record(db, Fan(client), match, CheerResult.WIN)

    assert len(_ranking(client, "victory", day, limit=2)["data"]) == 2
    r = client.get(f"{API}/rankings/victory", params={"limit": 0})
    assert r.status_code == 422
    r = client.get(f"{API}/rankings/victory", params={"date": "not-a-date"})
    assert r.status_code == 422


def test_ranking_judges_fairy_by_cumulative_records_like_me(
    client: TestClient, db: Session
) -> None:
    day = _new_day()
    earlier = [_match_on(db, day - timedelta(days=i)) for i in (1, 2, 3)]
    today = _match_on(db, day)
    later = _match_on(db, day + timedelta(days=1))

    # 이전에 3패, 오늘 1승 → 누적 1승3패(패배율 0.75): 오늘만 보면 승리요정이지만 패배요정이다
    loser = Fan(client)
    for m in earlier:
        _record(db, loser, m, CheerResult.LOSE)
    _record(db, loser, today, CheerResult.WIN)
    _record(db, loser, later, CheerResult.WIN)  # 그날 이후 기록은 세지 않는다

    # 이전에 1승1패, 오늘 1승 → 누적 2승1패(승률 0.67) 승리요정
    streak = Fan(client)
    _record(db, streak, earlier[0], CheerResult.WIN)
    _record(db, streak, earlier[1], CheerResult.LOSE)
    _record(db, streak, today, CheerResult.WIN)

    victory = {e["user_id"]: e for e in _ranking(client, "victory", day)["data"]}
    defeat = {e["user_id"]: e for e in _ranking(client, "defeat", day)["data"]}
    assert str(loser.id) not in victory
    assert defeat[str(loser.id)]["rate"] == 0.75
    assert defeat[str(loser.id)]["played"] == 4
    assert victory[str(streak.id)]["rate"] == 0.67
    assert victory[str(streak.id)]["played"] == 3


def test_ranking_matches_me_fairy_for_today(client: TestClient, db: Session) -> None:
    today = datetime.now(KST).date()
    past = [_match_on(db, today - timedelta(days=i)) for i in (1, 2)]
    now_match = _match_on(db, today)
    fan = Fan(client)
    _record(db, fan, past[0], CheerResult.LOSE)
    _record(db, fan, past[1], CheerResult.LOSE)
    _record(db, fan, now_match, CheerResult.WIN)  # 누적 1승2패 → 패배요정

    me = client.get(f"{API}/me", headers=fan.headers).json()
    assert me["fairy_type"] == "DEFEAT"
    ids = {e["user_id"] for e in _ranking(client, "defeat", today)["data"]}
    assert str(fan.id) in ids
    assert str(fan.id) not in {
        e["user_id"] for e in _ranking(client, "victory", today)["data"]
    }
