import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, delete, select

from app.core.config import settings
from app.models import (
    Badge,
    CheerRecord,
    CheerResult,
    Match,
    MatchStatus,
    PointReason,
    PointTransaction,
    Team,
    UserBadge,
)
from app.services import settlement

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
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        self.id = uuid.UUID(r.json()["user"]["id"])

    def me(self) -> dict:
        return self.client.get(f"{API}/me", headers=self.headers).json()

    def cheer(self, match: Match, home: bool) -> None:
        team = match.home_team_id if home else match.away_team_id
        r = self.client.post(
            f"{API}/matches/{match.id}/cheer",
            headers=self.headers,
            json={"cheered_team_id": str(team)},
        )
        assert r.status_code == 200, r.text


def _match(
    db: Session, days: int, status: MatchStatus = MatchStatus.SCHEDULED
) -> Match:
    t1, t2 = db.exec(select(Team).limit(2)).all()
    match = Match(
        home_team_id=t1.id,
        away_team_id=t2.id,
        league="KBO리그",
        kickoff_at=datetime.now(UTC) + timedelta(days=days),
        status=status,
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    _created_matches.append(match.id)
    return match


def _finish(
    client: TestClient, headers: dict[str, str], match: Match, home: int, away: int
) -> dict:
    r = client.patch(
        f"{API}/admin/matches/{match.id}/finish",
        headers=headers,
        json={"home_score": home, "away_score": away},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _badges(db: Session, user_id: uuid.UUID) -> set[str]:
    db.expire_all()
    rows = db.exec(
        select(Badge.code)
        .join(UserBadge, col(UserBadge.badge_id) == col(Badge.id))
        .where(UserBadge.user_id == user_id)
    ).all()
    return set(rows)


# --- 시드 / 순수 규칙 ---


def test_badges_seeded(db: Session) -> None:
    codes = set(db.exec(select(Badge.code)).all())
    assert {c for c, _, _ in settlement.BADGES} <= codes


def test_level_and_result_rules() -> None:
    assert settlement.level_for(0) == 1
    assert settlement.level_for(299) == 1
    assert settlement.level_for(300) == 2
    assert settlement.level_for(3820) == 13
    # 응원팀 기준 결과 (홈 2:1)
    assert settlement.result_for(True, 2, 1) == CheerResult.WIN
    assert settlement.result_for(False, 2, 1) == CheerResult.LOSE
    assert settlement.result_for(True, 1, 1) == CheerResult.DRAW
    assert settlement.result_for(False, 0, 3) == CheerResult.WIN


# --- grant_points ---


def test_grant_points_updates_total_level_and_guards_duplicates(
    client: TestClient, db: Session
) -> None:
    fan = Fan(client)
    settlement.grant_points(db, fan.id, 299, PointReason.DECIBEL_TOP3, "battle-1")
    db.commit()
    assert (fan.me()["total_points"], fan.me()["level"]) == (299, 1)

    settlement.grant_points(db, fan.id, 1, PointReason.DECIBEL_TOP3, "battle-2")
    db.commit()
    assert (fan.me()["total_points"], fan.me()["level"]) == (300, 2)

    # 같은 (유저, 사유, 대상)에는 두 번 지급할 수 없다
    with pytest.raises(IntegrityError):
        settlement.grant_points(db, fan.id, 100, PointReason.DECIBEL_TOP3, "battle-1")
    db.rollback()
    assert fan.me()["total_points"] == 300
    txs = db.exec(
        select(PointTransaction).where(PointTransaction.user_id == fan.id)
    ).all()
    assert sorted(t.amount for t in txs) == [1, 299]


# --- PATCH /admin/matches/{id}/finish ---


def test_finish_requires_superuser(
    client: TestClient,
    db: Session,
    normal_user_token_headers: dict[str, str],
) -> None:
    match = _match(db, 50)
    url = f"{API}/admin/matches/{match.id}/finish"
    body = {"home_score": 1, "away_score": 0}
    assert client.patch(url, json=body).status_code == 401
    assert (
        client.patch(url, headers=normal_user_token_headers, json=body).status_code
        == 403
    )
    db.refresh(match)
    assert match.status == MatchStatus.SCHEDULED


def test_finish_validation_and_not_found(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    h = superuser_token_headers
    r = client.patch(
        f"{API}/admin/matches/{uuid.uuid4()}/finish",
        headers=h,
        json={"home_score": 1, "away_score": 0},
    )
    assert r.status_code == 404
    match = _match(db, 50)
    for bad in ({"home_score": -1, "away_score": 0}, {"home_score": 1}):
        r = client.patch(f"{API}/admin/matches/{match.id}/finish", headers=h, json=bad)
        assert r.status_code == 422


def test_finish_settles_win_lose_and_points(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    match = _match(db, 51)
    home_fan, away_fan, lurker = Fan(client), Fan(client), Fan(client)
    home_fan.cheer(match, home=True)
    away_fan.cheer(match, home=False)  # lurker는 응원하지 않았다

    out = _finish(client, superuser_token_headers, match, 3, 1)
    assert (out["settled"], out["win"], out["draw"], out["lose"]) == (2, 1, 0, 1)
    assert out["match"]["status"] == "FINISHED"
    assert (out["match"]["home_score"], out["match"]["away_score"]) == (3, 1)
    assert out["match"]["finished_at"]

    win = home_fan.me()
    assert (win["total_points"], win["stats"]["win"], win["fairy_type"]) == (
        100,
        1,
        "VICTORY",
    )
    lose = away_fan.me()
    assert (lose["total_points"], lose["stats"]["lose"], lose["fairy_type"]) == (
        30,
        1,
        "DEFEAT",
    )
    assert lurker.me()["total_points"] == 0

    rec = client.get(f"{API}/me/records", headers=home_fan.headers).json()["data"][0]
    assert (rec["result"], rec["points_earned"]) == ("WIN", 100)

    tx = db.exec(
        select(PointTransaction).where(PointTransaction.user_id == home_fan.id)
    ).one()
    assert (tx.amount, tx.reason, tx.related_id) == (
        100,
        PointReason.MATCH_RESULT,
        str(match.id),
    )

    got = client.get(f"{API}/matches/{match.id}").json()
    assert (got["status"], got["home_score"], got["away_score"]) == ("FINISHED", 3, 1)


def test_finish_draw_gives_50_to_both_sides(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    match = _match(db, 52)
    a, b = Fan(client), Fan(client)
    a.cheer(match, home=True)
    b.cheer(match, home=False)
    out = _finish(client, superuser_token_headers, match, 2, 2)
    assert (out["win"], out["draw"], out["lose"]) == (0, 2, 0)
    assert a.me()["total_points"] == b.me()["total_points"] == 50
    # 무승부만 있으면 분모(승+패)가 0이라 중립요정
    assert a.me()["fairy_type"] == "NEUTRAL"


def test_finish_twice_is_409_and_does_not_double_pay(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    match = _match(db, 53)
    fan = Fan(client)
    fan.cheer(match, home=True)
    _finish(client, superuser_token_headers, match, 1, 0)
    r = client.patch(
        f"{API}/admin/matches/{match.id}/finish",
        headers=superuser_token_headers,
        json={"home_score": 0, "away_score": 5},
    )
    assert r.status_code == 409
    assert fan.me()["total_points"] == 100
    got = client.get(f"{API}/matches/{match.id}").json()
    assert (got["home_score"], got["away_score"]) == (1, 0)  # 점수도 바뀌지 않는다


def test_finish_is_atomic_when_settlement_fails(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    match = _match(db, 54)
    a, b = Fan(client), Fan(client)
    a.cheer(match, home=True)
    b.cheer(match, home=True)

    real = settlement.grant_points
    calls = {"n": 0}

    def flaky(*args, **kwargs):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("boom")
        return real(*args, **kwargs)

    monkeypatch.setattr(settlement, "grant_points", flaky)
    with pytest.raises(RuntimeError):
        client.patch(
            f"{API}/admin/matches/{match.id}/finish",
            headers=superuser_token_headers,
            json={"home_score": 1, "away_score": 0},
        )
    monkeypatch.undo()

    # 아무것도 반영되지 않았다: 경기는 그대로, 기록은 PENDING, 포인트 0
    got = client.get(f"{API}/matches/{match.id}").json()
    assert (got["status"], got["home_score"]) == ("SCHEDULED", None)
    assert a.me()["total_points"] == b.me()["total_points"] == 0
    for fan in (a, b):
        rec = client.get(f"{API}/me/records", headers=fan.headers).json()["data"][0]
        assert (rec["result"], rec["points_earned"]) == ("PENDING", 0)

    # 고쳐진 뒤 다시 종료하면 정상 정산된다
    _finish(client, superuser_token_headers, match, 1, 0)
    assert a.me()["total_points"] == b.me()["total_points"] == 100


def test_finish_leaves_other_matches_pending(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    m1, m2 = _match(db, 55), _match(db, 56)
    fan = Fan(client)
    fan.cheer(m1, home=True)
    fan.cheer(m2, home=True)
    _finish(client, superuser_token_headers, m1, 1, 0)
    records = {
        r["match_id"]: r
        for r in client.get(f"{API}/me/records", headers=fan.headers).json()["data"]
    }
    assert records[str(m1.id)]["result"] == "WIN"
    assert records[str(m2.id)]["result"] == "PENDING"
    assert fan.me()["stats"]["total"] == 1  # 진행 전 기록은 세지 않는다


# --- 배지 ---


def test_badges_victory_fairy_and_win_streak(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    fan = Fan(client)
    matches = [_match(db, d) for d in (60, 61, 62)]
    for i, m in enumerate(matches):
        fan.cheer(m, home=True)
        _finish(client, superuser_token_headers, m, 2, 0)
        got = _badges(db, fan.id)
        assert "VICTORY_FAIRY" in got  # 첫 승부터 승률 100%
        assert ("WIN_STREAK_3" in got) is (i == 2)  # 3연승은 세 번째에서야
    assert fan.me()["total_points"] == 300
    assert fan.me()["level"] == 2


def test_draw_breaks_win_streak(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    fan = Fan(client)
    for d, (h, a) in zip((63, 64, 65), ((1, 0), (1, 1), (1, 0)), strict=True):
        m = _match(db, d)
        fan.cheer(m, home=True)
        _finish(client, superuser_token_headers, m, h, a)
    assert "WIN_STREAK_3" not in _badges(db, fan.id)


def test_badge_defeat_fairy(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    fan = Fan(client)
    m = _match(db, 66)
    fan.cheer(m, home=False)
    _finish(client, superuser_token_headers, m, 1, 0)
    got = _badges(db, fan.id)
    assert "DEFEAT_FAIRY" in got
    assert "VICTORY_FAIRY" not in got


def test_badges_are_not_granted_twice_or_revoked(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    fan = Fan(client)
    m1, m2 = _match(db, 67), _match(db, 68)
    fan.cheer(m1, home=True)
    _finish(client, superuser_token_headers, m1, 1, 0)
    assert "VICTORY_FAIRY" in _badges(db, fan.id)

    fan.cheer(m2, home=True)
    _finish(client, superuser_token_headers, m2, 0, 3)  # 승률 50%로 떨어져도
    assert fan.me()["fairy_type"] != "VICTORY"  # 칭호는 바뀌지만
    assert "VICTORY_FAIRY" in _badges(db, fan.id)  # 얻은 배지는 그대로
    rows = db.exec(select(UserBadge).where(UserBadge.user_id == fan.id)).all()
    assert len(rows) == len({r.badge_id for r in rows})


def test_badge_steady_fan_needs_10_settled_matches(
    client: TestClient, db: Session
) -> None:
    fan = Fan(client)
    for i in range(10):
        m = _match(db, 70 + i)
        db.add(
            CheerRecord(
                user_id=fan.id,
                match_id=m.id,
                cheered_team_id=m.home_team_id,
                result=CheerResult.PENDING if i == 9 else CheerResult.DRAW,
            )
        )
    db.commit()
    settlement.evaluate_badges(db, fan.id)
    db.commit()
    assert "STEADY_FAN" not in _badges(db, fan.id)  # 확정 9건 + 진행 전 1건

    record = db.exec(
        select(CheerRecord).where(
            CheerRecord.user_id == fan.id, CheerRecord.result == CheerResult.PENDING
        )
    ).one()
    record.result = CheerResult.DRAW
    db.add(record)
    db.commit()
    assert settlement.evaluate_badges(db, fan.id) == ["STEADY_FAN"]
    db.commit()
    assert "STEADY_FAN" in _badges(db, fan.id)


def test_badge_decibel_master_threshold(client: TestClient, db: Session) -> None:
    fan = Fan(client)
    assert settlement.evaluate_badges(db, fan.id) == []
    assert settlement.evaluate_badges(db, fan.id, peak_db=109.9) == []
    assert settlement.evaluate_badges(db, fan.id, peak_db=110.0) == ["DECIBEL_MASTER"]
    db.commit()
    assert settlement.evaluate_badges(db, fan.id, peak_db=120.0) == []  # 중복 지급 없음
    assert _badges(db, fan.id) == {"DECIBEL_MASTER"}
