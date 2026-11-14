import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, select

from app.api.deps import SessionDep
from app.api.routes.matches import KST, _kst_day_range
from app.models import Community, CommunityPublic, Match

router = APIRouter(prefix="/communities", tags=["communities"])


def get_or_create_community(session: SessionDep, match_id: uuid.UUID) -> Community:
    community = session.exec(
        select(Community).where(Community.match_id == match_id)
    ).first()
    if community:
        return community
    community = Community(match_id=match_id)
    session.add(community)
    session.commit()
    session.refresh(community)
    return community


@router.get("/today", response_model=CommunityPublic)
def read_today_community(session: SessionDep) -> Any:
    """
    오늘(KST) 대표 경기(가장 이른 경기)의 커뮤니티. 없으면 만든다.
    """
    today = datetime.now(KST).date()
    start, end = _kst_day_range(today, today + timedelta(days=1))
    match = session.exec(
        select(Match)
        .where(col(Match.kickoff_at) >= start, col(Match.kickoff_at) < end)
        .order_by(col(Match.kickoff_at))
    ).first()
    if not match:
        raise HTTPException(status_code=404, detail="No match today")
    return get_or_create_community(session, match.id)
