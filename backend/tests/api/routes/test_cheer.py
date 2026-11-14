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
    """이 파일이 만든 경기만 지운다(응원 기록은 FK cascade). 다른 테스트의 월별·오늘 경기 개수에 영향이 없게."""
    yield
    if _created_matches:
        db.execute(delete(Match).where(col(Match.id).in_(_created_matches)))
        db.commit()


def _signup(client: TestClient) -> dict[str, str]:
    name = f"u{uuid.uuid4().hex[:12]}"
    r = client.post(f"{API}/auth/signup", json={"username": name, "password": "pw1234"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _today_match(client: TestClient) -> dict:
    return client.get(f"{API}/matches/today").json()["data"][0]


def _finished_match(db: Session) -> Match:
    return db.exec(select(Match).where(Match.status == MatchStatus.FINISHED)).first()  # type: ignore[return-value]


def _new_match(db: Session, status: MatchStatus, days: int) -> Match:
    """다른 테스트와 겹치지 않게 시드 팀으로 경기를 하나 더 만든다."""
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


# --- POST /matches/{id}/cheer ---


def test_cheer_requires_auth(client: TestClient) -> None:
    m = _today_match(client)
    r = client.post(
        f"{API}/matches/{m['id']}/cheer", json={"cheered_team_id": m["home_team_id"]}
    )
    assert r.status_code == 401


def test_cheer_creates_pending_then_updates(client: TestClient) -> None:
    h = _signup(client)
    m = _today_match(client)
    url = f"{API}/matches/{m['id']}/cheer"

    r = client.post(url, headers=h, json={"cheered_team_id": m["home_team_id"]})
    assert r.status_code == 200
    first = r.json()
    assert first["result"] == "PENDING"
    assert first["points_earned"] == 0
    assert first["cheered_team_id"] == m["home_team_id"]

    # 같은 경기에 다시 고르면 새 기록이 아니라 응원팀만 바뀐다
    r = client.post(url, headers=h, json={"cheered_team_id": m["away_team_id"]})
    assert r.status_code == 200
    assert r.json()["id"] == first["id"]
    assert r.json()["cheered_team_id"] == m["away_team_id"]

    records = client.get(f"{API}/me/records", headers=h).json()
    assert records["count"] == 1
    assert records["data"][0]["cheered_team_id"] == m["away_team_id"]


def test_cheer_same_team_is_idempotent(client: TestClient) -> None:
    h = _signup(client)
    m = _today_match(client)
    body = {"cheered_team_id": m["home_team_id"]}
    a = client.post(f"{API}/matches/{m['id']}/cheer", headers=h, json=body).json()
    b = client.post(f"{API}/matches/{m['id']}/cheer", headers=h, json=body).json()
    assert a["id"] == b["id"]


def test_cheer_rejects_team_not_in_match(client: TestClient, db: Session) -> None:
    h = _signup(client)
    m = _today_match(client)
    outsider = db.exec(
        select(Team).where(col(Team.id).not_in([m["home_team_id"], m["away_team_id"]]))
    ).first()
    assert outsider
    r = client.post(
        f"{API}/matches/{m['id']}/cheer",
        headers=h,
        json={"cheered_team_id": str(outsider.id)},
    )
    assert r.status_code == 400
    r = client.post(
        f"{API}/matches/{m['id']}/cheer",
        headers=h,
        json={"cheered_team_id": str(uuid.uuid4())},
    )
    assert r.status_code == 400


def test_cheer_finished_match_is_409(client: TestClient, db: Session) -> None:
    h = _signup(client)
    match = _finished_match(db)
    r = client.post(
        f"{API}/matches/{match.id}/cheer",
        headers=h,
        json={"cheered_team_id": str(match.home_team_id)},
    )
    assert r.status_code == 409


def test_cheer_match_not_found(client: TestClient) -> None:
    h = _signup(client)
    r = client.post(
        f"{API}/matches/{uuid.uuid4()}/cheer",
        headers=h,
        json={"cheered_team_id": str(uuid.uuid4())},
    )
    assert r.status_code == 404


def test_cheer_settled_record_cannot_change(client: TestClient, db: Session) -> None:
    """정산으로 확정된 기록은 경기가 아직 끝나지 않은 것처럼 보여도 바꿀 수 없다."""
    h = _signup(client)
    m = _today_match(client)
    url = f"{API}/matches/{m['id']}/cheer"
    rec_id = client.post(
        url, headers=h, json={"cheered_team_id": m["home_team_id"]}
    ).json()["id"]
    record = db.get(CheerRecord, uuid.UUID(rec_id))
    assert record
    record.result = CheerResult.WIN
    db.add(record)
    db.commit()
    r = client.post(url, headers=h, json={"cheered_team_id": m["away_team_id"]})
    assert r.status_code == 409


# --- GET /me/records, /me/stats ---


def _record(
    db: Session, headers_user_id: str, match: Match, result: CheerResult
) -> None:
    db.add(
        CheerRecord(
            user_id=uuid.UUID(headers_user_id),
            match_id=match.id,
            cheered_team_id=match.home_team_id,
            result=result,
            points_earned={"WIN": 100, "DRAW": 50, "LOSE": 30, "PENDING": 0}[
                result.value
            ],
        )
    )
    db.commit()


def test_records_and_stats_empty(client: TestClient) -> None:
    h = _signup(client)
    assert client.get(f"{API}/me/records", headers=h).json() == {
        "data": [],
        "count": 0,
        "page": 1,
        "size": 20,
    }
    stats = client.get(f"{API}/me/stats", headers=h).json()
    assert stats == {
        "total": 0,
        "win": 0,
        "draw": 0,
        "lose": 0,
        "win_rate": 0.0,
        "lose_rate": 0.0,
    }


def test_stats_count_only_settled_and_drive_fairy(
    client: TestClient, db: Session
) -> None:
    h = _signup(client)
    uid = client.get(f"{API}/me", headers=h).json()["id"]
    # 승2 무1 패1 + 진행 전 1건 (명세 §3.1: 분모는 승+패)
    for result in (
        CheerResult.WIN,
        CheerResult.WIN,
        CheerResult.DRAW,
        CheerResult.LOSE,
        CheerResult.PENDING,
    ):
        _record(db, uid, _new_match(db, MatchStatus.SCHEDULED, 30), result)

    stats = client.get(f"{API}/me/stats", headers=h).json()
    assert stats == {
        "total": 4,
        "win": 2,
        "draw": 1,
        "lose": 1,
        "win_rate": 0.67,
        "lose_rate": 0.33,
    }

    me = client.get(f"{API}/me", headers=h).json()
    assert me["stats"] == stats
    assert me["fairy_type"] == "VICTORY"  # 승률 66.7% >= 60%
    assert me["fairy_label"].startswith("승리요정 ")


def test_stats_defeat_fairy(client: TestClient, db: Session) -> None:
    h = _signup(client)
    uid = client.get(f"{API}/me", headers=h).json()["id"]
    for result in (CheerResult.WIN, CheerResult.LOSE, CheerResult.LOSE):
        _record(db, uid, _new_match(db, MatchStatus.SCHEDULED, 30), result)
    me = client.get(f"{API}/me", headers=h).json()
    assert me["fairy_type"] == "DEFEAT"  # 승률 33% < 60%, 패배율 67% >= 30%


def test_records_order_pagination_and_isolation(
    client: TestClient, db: Session
) -> None:
    h, other = _signup(client), _signup(client)
    uid = client.get(f"{API}/me", headers=h).json()["id"]
    other_id = client.get(f"{API}/me", headers=other).json()["id"]
    matches = [_new_match(db, MatchStatus.SCHEDULED, d) for d in (40, 42, 41)]
    for m in matches:
        _record(db, uid, m, CheerResult.PENDING)
    _record(db, other_id, matches[0], CheerResult.WIN)  # 남의 기록은 섞이지 않는다

    body = client.get(f"{API}/me/records", headers=h).json()
    assert body["count"] == 3
    kickoffs = [r["match"]["kickoff_at"] for r in body["data"]]
    assert kickoffs == sorted(kickoffs, reverse=True)  # 최근 경기 순
    item = body["data"][0]
    assert item["match"]["home_team"]["name"]
    assert {"result", "points_earned", "cheered_team_id", "created_at"} <= set(item)

    p1 = client.get(
        f"{API}/me/records", headers=h, params={"page": 1, "size": 2}
    ).json()
    p2 = client.get(
        f"{API}/me/records", headers=h, params={"page": 2, "size": 2}
    ).json()
    assert (len(p1["data"]), len(p2["data"]), p1["count"]) == (2, 1, 3)
    assert {r["id"] for r in p1["data"]}.isdisjoint({r["id"] for r in p2["data"]})

    for bad in ({"page": 0}, {"size": 0}, {"size": 101}):
        assert client.get(f"{API}/me/records", headers=h, params=bad).status_code == 422
