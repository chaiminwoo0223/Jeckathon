import json
import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, select

from app.ai import fortune as ai
from app.ai import fortune_seed
from app.core.config import settings
from app.models import Match, MatchStatus, Team

API = settings.API_V1_STR


@pytest.fixture
def match(db: Session) -> Generator[tuple[Match, Team, Team]]:
    home, away = db.exec(select(Team).limit(2)).all()
    m = Match(
        home_team_id=home.id,
        away_team_id=away.id,
        league="KBO리그",
        kickoff_at=datetime.now(UTC) + timedelta(days=200),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    yield m, home, away
    db.execute(delete(Match).where(col(Match.id) == m.id))
    db.commit()


def _get(client: TestClient, m: Match, team: Team):  # type: ignore[no-untyped-def]
    return client.get(f"{API}/matches/{m.id}/fortune", params={"team_id": str(team.id)})


def test_fortune_is_stable_and_differs_per_team(
    client: TestClient, match: tuple[Match, Team, Team]
) -> None:
    m, home, away = match
    r = _get(client, m, home)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["match_id"] == str(m.id) and body["team_id"] == str(home.id)
    assert body["fortune_text"] and body["cheer_tip"]
    assert 0 <= body["luck_score"] <= 100
    assert _get(client, m, home).json() == body  # 새로고침해도 같다
    other = _get(client, m, away).json()
    assert other["fortune_text"] != body["fortune_text"]  # 홈·원정 문구가 다르다
    assert other["cheer_tip"] != body["cheer_tip"]


def test_fortune_validation(
    client: TestClient, match: tuple[Match, Team, Team], db: Session
) -> None:
    m, home, _ = match
    stranger = db.exec(
        select(Team).where(col(Team.id).notin_([m.home_team_id, m.away_team_id]))
    ).first()
    assert stranger is not None
    assert _get(client, m, stranger).status_code == 400
    r = client.get(
        f"{API}/matches/{uuid.uuid4()}/fortune", params={"team_id": str(home.id)}
    )
    assert r.status_code == 404
    assert client.get(f"{API}/matches/{m.id}/fortune").status_code == 422


def test_every_seeded_match_gets_a_fortune(client: TestClient, db: Session) -> None:
    matches = db.exec(select(Match).limit(200)).all()
    assert matches
    for m in matches:
        for team_id in (m.home_team_id, m.away_team_id):
            r = client.get(
                f"{API}/matches/{m.id}/fortune", params={"team_id": str(team_id)}
            )
            assert r.status_code == 200, r.text


def test_pick_varies_by_date_and_never_collides_within_a_match() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    start = date(2026, 4, 1)
    days = [start + timedelta(days=i) for i in range(60)]
    picks = [fortune_seed.pick_fortune(d, a, b, "LG") for d in days]
    assert len({p.fortune_text for p in picks}) > 15  # 날짜가 바뀌면 달라진다
    for d in days:
        mine = fortune_seed.pick_fortune(d, a, b, "LG")
        theirs = fortune_seed.pick_fortune(d, b, a, "두산")
        assert mine.fortune_text.replace("LG", "") != theirs.fortune_text.replace(
            "두산", ""
        )
        assert mine.cheer_tip != theirs.cheer_tip


def test_seed_pool_is_valid() -> None:
    pool = json.loads(fortune_seed.SEED_FILE.read_text(encoding="utf-8"))
    assert 0 <= pool["score_min"] <= pool["score_max"] <= 100
    assert len(pool["fortune_texts"]) >= 30 and len(pool["cheer_tips"]) >= 30
    assert all(0 < len(t) <= 500 for t in pool["fortune_texts"])  # Fortune.fortune_text
    assert all(0 < len(t) <= 300 for t in pool["cheer_tips"])  # Fortune.cheer_tip


def test_recent_form(db: Session, match: tuple[Match, Team, Team]) -> None:
    m, home, away = match
    past = [
        Match(
            home_team_id=home.id,
            away_team_id=away.id,
            league="KBO리그",
            kickoff_at=m.kickoff_at - timedelta(days=d),
            status=MatchStatus.FINISHED,
            home_score=hs,
            away_score=as_,
        )
        for d, hs, as_ in [(1, 5, 2), (2, 1, 3), (3, 4, 4)]
    ]
    db.add_all(past)
    db.commit()
    try:
        home_form = ai.recent_form(
            db, m, home.id
        )  # 시드된 이전 경기가 뒤에 붙을 수 있다
        assert home_form is not None and home_form.startswith("WLD")
        away_form = ai.recent_form(db, m, away.id)
        assert away_form is not None and away_form.startswith("LWD")
    finally:
        db.execute(delete(Match).where(col(Match.id).in_([p.id for p in past])))
        db.commit()


def test_parse_draft() -> None:
    ok = ai.parse_draft(
        '설명 {"fortune_text": "좋아요", "cheer_tip": "팁", "luck_score": 150} 끝'
    )
    assert ok == ai.FortuneDraft("좋아요", "팁", 100)
    assert ai.parse_draft("JSON 없음") is None
