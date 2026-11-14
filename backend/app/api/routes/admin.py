import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select

from app.api.deps import SessionDep, get_current_active_superuser
from app.api.routes.matches import to_match_details
from app.models import (
    CheerResult,
    Match,
    MatchFinishIn,
    MatchFinishOut,
    MatchStatus,
)
from app.services import settlement

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.patch("/matches/{id}/finish", response_model=MatchFinishOut)
def finish_match(session: SessionDep, id: uuid.UUID, body: MatchFinishIn) -> Any:
    """
    경기 종료를 발동한다(데모용 수동 트리거). 한 트랜잭션으로 스코어 저장, 응원 기록 확정,
    포인트 지급, 배지 평가를 끝낸다. 이미 종료된 경기는 409.
    """
    # 동시에 두 번 눌러도 포인트가 두 번 나가지 않게 경기 행을 잠근다.
    match = session.exec(select(Match).where(Match.id == id).with_for_update()).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if match.status == MatchStatus.FINISHED:
        raise HTTPException(status_code=409, detail="Match already finished")
    try:
        counts = settlement.settle_match(
            session, match, body.home_score, body.away_score
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(match)
    return MatchFinishOut(
        match=to_match_details(session, [match])[0],
        settled=sum(counts.values()),
        win=counts[CheerResult.WIN],
        draw=counts[CheerResult.DRAW],
        lose=counts[CheerResult.LOSE],
    )
