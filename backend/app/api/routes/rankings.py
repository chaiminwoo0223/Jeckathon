import uuid
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlmodel import Session, col, select

from app.api.deps import SessionDep
from app.models import (
    CheerRecord,
    CheerResult,
    FairyType,
    Match,
    RankingEntryPublic,
    RankingPublic,
    User,
    UserSetting,
)
from app.services import stats as stats_service

router = APIRouter(prefix="/rankings", tags=["rankings"])

KST = timezone(timedelta(hours=9))  # 경기 날짜는 한국 시간 기준(명세 §4.2)


def _day_range(day: date) -> tuple[datetime, datetime]:
    """KST 하루 [day, day+1)를 UTC 시각 범위로 바꾼다."""
    start = datetime.combine(day, datetime.min.time(), tzinfo=KST)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


def _ranking(session: Session, kind: FairyType, day: date, limit: int) -> RankingPublic:
    """그날(KST) 킥오프한 경기의 확정된 응원 기록으로 요정 랭킹을 만든다.

    - 후보: 그날 확정 기록이 있고 랭킹 공개(`ranking_public`, 설정 행이 없으면 공개)인 유저.
    - 승률·패배율·요정 판정은 §3.1·§3.2 함수(`services/stats.py`)를 그대로 쓴다.
    - 그 종류의 요정인 유저만 올린다(승리요정이 우선이라 승률 60% 이상은 패배요정 랭킹에 없다).
    - 정렬: 비율 내림차순 → 경기 수 내림차순 → user_id(동률일 때 순서가 흔들리지 않게).
    """
    start, end = _day_range(day)
    rows = session.exec(
        select(CheerRecord.user_id, CheerRecord.result)
        .join(Match, col(Match.id) == col(CheerRecord.match_id))
        .outerjoin(UserSetting, col(UserSetting.user_id) == col(CheerRecord.user_id))
        .where(
            col(Match.kickoff_at) >= start,
            col(Match.kickoff_at) < end,
            CheerRecord.result != CheerResult.PENDING,
            col(UserSetting.ranking_public).is_not(False),
        )
    ).all()

    counts: dict[uuid.UUID, dict[CheerResult, int]] = {}
    for user_id, result in rows:
        result = CheerResult(result)
        per_user = counts.setdefault(user_id, {})
        per_user[result] = per_user.get(result, 0) + 1

    candidates: list[tuple[uuid.UUID, float, int, int, int]] = []
    for user_id, c in counts.items():
        win = c.get(CheerResult.WIN, 0)
        draw = c.get(CheerResult.DRAW, 0)
        lose = c.get(CheerResult.LOSE, 0)
        if stats_service.fairy_type(win=win, lose=lose) != kind:
            continue
        win_rate, lose_rate = stats_service.rates(win, lose)
        rate = win_rate if kind == FairyType.VICTORY else lose_rate
        candidates.append((user_id, rate, win, draw, lose))
    candidates.sort(key=lambda t: (-t[1], -(t[2] + t[3] + t[4]), str(t[0])))
    candidates = candidates[:limit]

    users = {
        u.id: u
        for u in session.exec(
            select(User).where(col(User.id).in_([t[0] for t in candidates]))
        ).all()
    }
    data = []
    for rank, (user_id, rate, win, draw, lose) in enumerate(candidates, start=1):
        user = users[user_id]
        data.append(
            RankingEntryPublic(
                rank=rank,
                user_id=user_id,
                nickname=user.display_nickname,
                fairy_label=stats_service.fairy_label(kind, user.display_nickname),
                profile_image_url=user.profile_image_url,
                rate=round(rate, 2),
                played=win + draw + lose,
                win=win,
                draw=draw,
                lose=lose,
            )
        )
    return RankingPublic(date=day, kind=kind, data=data, count=len(data))


@router.get("/victory", response_model=RankingPublic)
def read_victory_ranking(
    session: SessionDep,
    date: date | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Any:
    """
    오늘의 승리요정 랭킹(승률 내림차순). `date`는 KST 기준이고 생략하면 오늘이다.
    """
    return _ranking(session, FairyType.VICTORY, date or datetime.now(KST).date(), limit)


@router.get("/defeat", response_model=RankingPublic)
def read_defeat_ranking(
    session: SessionDep,
    date: date | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Any:
    """
    오늘의 패배요정 랭킹(패배율 내림차순). `date`는 KST 기준이고 생략하면 오늘이다.
    """
    return _ranking(session, FairyType.DEFEAT, date or datetime.now(KST).date(), limit)
