"""KBO teams and schedule seed.

- Teams: the 10 KBO clubs with the short name / color the UI draws as a logo.
- Season: real games from kbo_<season>.json (scripts/fetch_kbo_schedule.py).
- Demo: the season is over by November, so if today (KST) has no game we add
  demo games for today and a few days ahead, so the calendar → cheer →
  community flow always has a game to start from.

Every step only inserts what is missing, so it is safe to run on each start.
"""

import json
from datetime import UTC, date, datetime, time, timedelta, timezone
from pathlib import Path

from sqlmodel import Session, col, select

from app.models import Match, MatchStatus, Team

LEAGUE = "KBO리그"
KST = timezone(timedelta(hours=9))
SEED_DIR = Path(__file__).parent
SEASONS = (2026,)

# name, full name, short name, color
KBO_TEAMS = [
    ("LG", "LG 트윈스", "LG", "#C30452"),
    ("두산", "두산 베어스", "DOO", "#131230"),
    ("KIA", "KIA 타이거즈", "KIA", "#EA0029"),
    ("삼성", "삼성 라이온즈", "SAM", "#074CA1"),
    ("롯데", "롯데 자이언츠", "LOT", "#041E42"),
    ("한화", "한화 이글스", "HAN", "#FC4E00"),
    ("SSG", "SSG 랜더스", "SSG", "#CE0E2D"),
    ("NC", "NC 다이노스", "NC", "#315288"),
    ("KT", "KT 위즈", "KT", "#000000"),
    ("키움", "키움 히어로즈", "KIW", "#570514"),
]

# (home, away, days from today) — today's pair matches the spec §7 demo scenario
DEMO_FIXTURES = [
    ("LG", "두산", 0),
    ("KIA", "삼성", 0),
    ("SSG", "롯데", 2),
    ("삼성", "LG", 5),
]
DEMO_KICKOFF = time(18, 30)


def seed_kbo(session: Session) -> None:
    teams = _seed_teams(session)
    for season in SEASONS:
        _seed_season(session, teams, season)
    _seed_demo(session, teams)


def _seed_teams(session: Session) -> dict[str, Team]:
    teams = {t.name: t for t in session.exec(select(Team)).all()}
    for name, full_name, short_name, color in KBO_TEAMS:
        team = teams.get(name)
        if team is None:
            team = Team(name=name, full_name=full_name, league=LEAGUE)
            teams[name] = team
        team.short_name = team.short_name or short_name
        team.color = team.color or color
        session.add(team)
    session.commit()
    return teams


def _seed_season(session: Session, teams: dict[str, Team], season: int) -> None:
    path = SEED_DIR / f"kbo_{season}.json"
    if not path.exists():
        return
    games = json.loads(path.read_text())["games"]
    existing = {
        (m.home_team_id, m.away_team_id, m.kickoff_at.astimezone(UTC))
        for m in session.exec(select(Match)).all()
    }
    for g in games:
        kickoff = datetime.fromisoformat(g["kickoff_at"]).astimezone(UTC)
        home, away = teams[g["home"]], teams[g["away"]]
        if (home.id, away.id, kickoff) in existing:
            continue
        finished = g["home_score"] is not None
        session.add(
            Match(
                home_team_id=home.id,
                away_team_id=away.id,
                league=LEAGUE,
                kickoff_at=kickoff,
                status=MatchStatus.FINISHED if finished else MatchStatus.SCHEDULED,
                home_score=g["home_score"],
                away_score=g["away_score"],
                finished_at=kickoff + timedelta(hours=3) if finished else None,
                venue=g["venue"],
                round_label=g["round_label"],
            )
        )
    session.commit()


def _has_match_on(session: Session, day: date) -> bool:
    start = datetime.combine(day, time.min, tzinfo=KST)
    return (
        session.exec(
            select(Match.id).where(
                col(Match.kickoff_at) >= start,
                col(Match.kickoff_at) < start + timedelta(days=1),
            )
        ).first()
        is not None
    )


def _seed_demo(session: Session, teams: dict[str, Team]) -> None:
    today = datetime.now(KST).date()
    by_day: dict[int, list[tuple[str, str]]] = {}
    for home, away, offset in DEMO_FIXTURES:
        by_day.setdefault(offset, []).append((home, away))
    for offset, pairs in by_day.items():
        day = today + timedelta(days=offset)
        if _has_match_on(session, day):
            continue
        kickoff = datetime.combine(day, DEMO_KICKOFF, tzinfo=KST)
        for home, away in pairs:
            session.add(
                Match(
                    home_team_id=teams[home].id,
                    away_team_id=teams[away].id,
                    league=LEAGUE,
                    kickoff_at=kickoff,
                    status=MatchStatus.SCHEDULED,
                    venue=_home_venue(home),
                )
            )
    session.commit()


_VENUES = {
    "LG": "잠실",
    "두산": "잠실",
    "KIA": "광주",
    "삼성": "대구",
    "롯데": "사직",
    "한화": "대전",
    "SSG": "문학",
    "NC": "창원",
    "KT": "수원",
    "키움": "고척",
}


def _home_venue(team: str) -> str:
    return _VENUES.get(team, "")
