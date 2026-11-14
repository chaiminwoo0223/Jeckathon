import json
import uuid
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, delete, select

from app.ai import fortune as ai
from app.ai import fortune_players, fortune_seed
from app.core.config import settings
from app.models import FortuneGrade, Match, MatchStatus, Player, Team

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


# --- 선수 생년월일 운세 (fortune_players) ---


def _player(kbo_id: int, birth: date, number: str | None = "10") -> Player:
    return Player(
        kbo_id=kbo_id,
        team_id=uuid.uuid4(),
        name=f"선수{kbo_id}",
        position="투수",
        back_number=number,
        birth_date=birth,
    )


def _roster(n: int, start: int = 1) -> list[Player]:
    base = date(1990, 1, 1)
    return [_player(start + i, base + timedelta(days=i * 37)) for i in range(n)]


def test_grade_boundaries() -> None:
    expected = {
        0: "대흉", 7: "대흉", 8: "중흉", 22: "중흉", 23: "소흉", 42: "소흉",
        43: "소길", 67: "소길", 68: "중길", 87: "중길", 88: "대길", 99: "대길",
    }  # fmt: skip
    for score, grade in expected.items():
        assert fortune_players.grade_of(score).value == grade, score


def test_player_score_is_stable_and_birth_driven() -> None:
    d = date(2026, 11, 14)
    b = date(1998, 3, 4)
    assert fortune_players.player_score(b, d) == fortune_players.player_score(b, d)
    assert 0 <= fortune_players.player_score(b, d) <= 99
    days = [date(2026, 4, 1) + timedelta(days=i) for i in range(60)]
    assert len({fortune_players.player_score(b, x) for x in days}) > 30  # 날짜마다 다름
    births = [date(1990, 1, 1) + timedelta(days=i * 11) for i in range(60)]
    assert (
        len({fortune_players.player_score(x, d) for x in births}) > 30
    )  # 생일마다 다름


def test_candidates_exclude_three_digit_and_missing_numbers() -> None:
    b = date(1999, 1, 1)
    assert fortune_players.is_candidate(_player(1, b, "0"))
    assert fortune_players.is_candidate(_player(2, b, "00"))
    assert fortune_players.is_candidate(_player(3, b, "99"))
    assert not fortune_players.is_candidate(_player(4, b, "102"))
    assert not fortune_players.is_candidate(_player(5, b, None))
    assert not fortune_players.is_candidate(_player(6, b, "A1"))


def test_team_score_spreads_across_all_six_grades() -> None:
    # 팀마다 다른 후보 65명 × 여러 날짜로 등급 분포를 본다. 한 등급에 쏠리면 안 된다.
    counts: dict[str, int] = {}
    for team_i in range(40):
        roster = _roster(65, start=team_i * 100)
        for offset in range(0, 600, 60):
            day = date(2026, 3, 1) + timedelta(days=offset + team_i)
            scores = [fortune_players.player_score(p.birth_date, day) for p in roster]
            g = fortune_players.grade_of(fortune_players.team_score(scores)).value
            counts[g] = counts.get(g, 0) + 1
    total = sum(counts.values())
    assert set(counts) == {"대길", "중길", "소길", "소흉", "중흉", "대흉"}, counts
    assert all(c / total < 0.4 for c in counts.values()), counts
    assert 0 <= fortune_players.team_score([0] * 65) <= 5
    assert 95 <= fortune_players.team_score([99] * 65) <= 100


def test_build_fortune_shape_and_rules() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    me = fortune_players.Side(
        a, "LG", _roster(65, 1) + [_player(900, date(2000, 1, 1), "103")]
    )
    other = fortune_players.Side(b, "두산", _roster(65, 1000))
    day = date(2026, 11, 14)
    r = fortune_players.build_fortune(day, me, other)
    assert r.draft.fortune_text and r.draft.cheer_tip
    assert "{team}" not in r.draft.fortune_text and "{player}" not in str(r)
    assert 0 <= r.draft.luck_score <= 100
    assert fortune_players.grade_of(r.draft.luck_score) == r.grade
    assert len(r.lucky_players) == 3
    scores = [p.luck_score for p in r.lucky_players]
    assert scores == sorted(scores, reverse=True)
    assert all(p.kbo_id != 900 for p in r.lucky_players)  # 육성 번호 제외
    assert all(p.one_liner and p.name in p.one_liner for p in r.lucky_players)
    # 65명 중 최하위는 사실상 항상 흉 계열이고, lucky와 겹치지 않는다
    assert r.caution_player is not None
    assert r.caution_player.grade in fortune_players.BAD_GRADES
    assert r.caution_player.kbo_id not in {p.kbo_id for p in r.lucky_players}
    assert fortune_players.build_fortune(day, me, other) == r  # 결정적


def test_build_fortune_falls_back_with_few_candidates() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    me = fortune_players.Side(a, "LG", _roster(3))
    other = fortune_players.Side(b, "두산", [])
    r = fortune_players.build_fortune(date(2026, 11, 14), me, other)
    assert r.lucky_players == [] and r.caution_player is None
    assert r.draft.fortune_text and 0 <= r.draft.luck_score <= 100
    assert fortune_players.grade_of(r.draft.luck_score) == r.grade


def test_two_teams_never_share_text_even_with_same_grade() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    same = _roster(65, 1)  # 같은 선수진이면 같은 등급이 된다
    clone = [_player(p.kbo_id + 5000, p.birth_date) for p in same]
    for i in range(80):
        day = date(2026, 3, 1) + timedelta(days=i)
        mine = fortune_players.build_fortune(
            day,
            fortune_players.Side(a, "LG", same),
            fortune_players.Side(b, "두산", clone),
        )
        theirs = fortune_players.build_fortune(
            day,
            fortune_players.Side(b, "두산", clone),
            fortune_players.Side(a, "LG", same),
        )
        assert mine.grade == theirs.grade
        assert mine.draft.fortune_text.replace(
            "LG", ""
        ) != theirs.draft.fortune_text.replace("두산", "")
        assert mine.draft.cheer_tip != theirs.draft.cheer_tip


def test_grades_seed_is_valid() -> None:
    pool = json.loads(fortune_players.GRADES_FILE.read_text(encoding="utf-8"))
    assert pool["grades"] == [g.value for g in FortuneGrade]
    for grade in pool["grades"]:
        g = pool["team"][grade]
        assert len(g["fortune_texts"]) >= 8 and len(g["cheer_tips"]) >= 8
        assert len(g["player_one_liners"]) >= 10
        assert all("{team}" in t and len(t) <= 500 for t in g["fortune_texts"])
        assert all(0 < len(t) <= 300 for t in g["cheer_tips"])
        assert all("{player}" in t for t in g["player_one_liners"])
        for key in ("fortune_texts", "cheer_tips", "player_one_liners"):
            assert len(set(g[key])) == len(g[key])  # 같은 풀 안 중복 없음
    # 흉 계열 팀 문구·팁은 응원으로 맺는다(데시벨 대결 연결)
    for grade in ("중흉", "대흉"):
        assert any("응원" in t for t in pool["team"][grade]["cheer_tips"])


def test_seeded_players_and_api_fields(client: TestClient, db: Session) -> None:
    assert len(db.exec(select(Player.id)).all()) >= 1000
    m = db.exec(select(Match).order_by(col(Match.kickoff_at).desc())).first()
    assert m is not None
    r = _get(client, m, db.get(Team, m.home_team_id))  # type: ignore[arg-type]
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["grade"] in {g.value for g in FortuneGrade}
    assert len(body["lucky_players"]) == 3
    p = body["lucky_players"][0]
    assert set(p) == {
        "kbo_id", "name", "position", "back_number", "birth_year",
        "grade", "luck_score", "one_liner",
    }  # fmt: skip
    assert "birth_date" not in p and 1970 < p["birth_year"] < 2010
