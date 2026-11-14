import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.api.deps import SessionDep
from app.models import (
    Match,
    MatchDay,
    MatchDetail,
    MatchesByMonth,
    MatchesToday,
    Team,
    TeamPublic,
)

router = APIRouter(prefix="/matches", tags=["matches"])

KST = timezone(timedelta(hours=9))  # 경기 날짜는 한국 시간 기준으로 묶는다


def _to_details(session: SessionDep, matches: list[Match]) -> list[MatchDetail]:
    team_ids = {m.home_team_id for m in matches} | {m.away_team_id for m in matches}
    teams: dict[uuid.UUID, Team] = {}
    if team_ids:
        rows = session.exec(select(Team).where(col(Team.id).in_(team_ids))).all()
        teams = {t.id: t for t in rows}
    return [
        MatchDetail(
            **m.model_dump(),
            home_team=TeamPublic.model_validate(teams[m.home_team_id]),
            away_team=TeamPublic.model_validate(teams[m.away_team_id]),
        )
        for m in matches
    ]


def _kst_day_range(start: date, end: date) -> tuple[datetime, datetime]:
    """KST 날짜 [start, end) 를 UTC 시각 범위로 바꾼다."""
    return (
        datetime.combine(start, datetime.min.time(), tzinfo=KST).astimezone(UTC),
        datetime.combine(end, datetime.min.time(), tzinfo=KST).astimezone(UTC),
    )


@router.get("/", response_model=MatchesByMonth)
def read_matches_by_month(
    session: SessionDep,
    month: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
) -> Any:
    """
    월별 경기 (캘린더용). 경기가 있는 날짜별로 그룹.
    """
    year, mon = (int(x) for x in month.split("-"))
    first = date(year, mon, 1)
    next_first = date(year + 1, 1, 1) if mon == 12 else date(year, mon + 1, 1)
    start, end = _kst_day_range(first, next_first)

    matches = list(
        session.exec(
            select(Match)
            .where(col(Match.kickoff_at) >= start, col(Match.kickoff_at) < end)
            .order_by(col(Match.kickoff_at))
        ).all()
    )
    grouped: dict[date, list[MatchDetail]] = defaultdict(list)
    for detail in _to_details(session, matches):
        grouped[detail.kickoff_at.astimezone(KST).date()].append(detail)
    return MatchesByMonth(
        month=month,
        days=[MatchDay(date=d, matches=grouped[d]) for d in sorted(grouped)],
        count=len(matches),
    )


@router.get("/today", response_model=MatchesToday)
def read_matches_today(session: SessionDep) -> Any:
    """
    오늘(KST) 경기 목록.
    """
    today = datetime.now(KST).date()
    start, end = _kst_day_range(today, today + timedelta(days=1))
    matches = list(
        session.exec(
            select(Match)
            .where(col(Match.kickoff_at) >= start, col(Match.kickoff_at) < end)
            .order_by(col(Match.kickoff_at))
        ).all()
    )
    details = _to_details(session, matches)
    return MatchesToday(date=today, data=details, count=len(details))


@router.get("/{id}", response_model=MatchDetail)
def read_match(session: SessionDep, id: uuid.UUID) -> Any:
    """
    경기 상세 (팀, 시각, 상태, 스코어).
    """
    match = session.get(Match, id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return _to_details(session, [match])[0]
