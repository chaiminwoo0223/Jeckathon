from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Badge,
    PointsPublic,
    PointTransaction,
    PointTransactionPublic,
    UserBadge,
    UserBadgePublic,
    UserBadgesPublic,
)

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/points", response_model=PointsPublic)
def read_my_points(
    session: SessionDep,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Any:
    """
    내 포인트 내역. 최신순, 1부터 시작하는 page.
    """
    where = PointTransaction.user_id == current_user.id
    count = session.exec(
        select(func.count()).select_from(PointTransaction).where(where)
    ).one()
    rows = session.exec(
        select(PointTransaction)
        .where(where)
        .order_by(col(PointTransaction.created_at).desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return PointsPublic(
        data=[PointTransactionPublic.model_validate(t) for t in rows],
        count=count,
        page=page,
        size=size,
        total_points=current_user.total_points,
    )


@router.get("/badges", response_model=UserBadgesPublic)
def read_my_badges(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    내가 얻은 배지. 최근 획득 순.
    """
    rows = session.exec(
        select(Badge, UserBadge)
        .join(UserBadge, col(UserBadge.badge_id) == col(Badge.id))
        .where(UserBadge.user_id == current_user.id)
        .order_by(col(UserBadge.acquired_at).desc())
    ).all()
    data = [
        UserBadgePublic(**badge.model_dump(), acquired_at=ub.acquired_at)
        for badge, ub in rows
    ]
    return UserBadgesPublic(data=data, count=len(data))
