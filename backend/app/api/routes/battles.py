import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import case, func
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import col, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Battle,
    BattleCreate,
    BattleMe,
    BattleRecord,
    BattleRecordSubmit,
    BattleResult,
    BattleState,
    BattleStatus,
    Community,
    LeaderboardEntry,
    User,
)

router = APIRouter(tags=["battles"])


def _get_battle(session: SessionDep, id: uuid.UUID) -> Battle:
    """대결을 읽고, endsAt이 지났으면 그 자리에서 FINISHED로 바꾼다(지연 정산, 명세 §4.6)."""
    battle = session.get(Battle, id)
    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")
    if (
        battle.status == BattleStatus.ONGOING
        and battle.ends_at
        and datetime.now(UTC) >= battle.ends_at
    ):
        # shortcut: TOP3 포인트(100/50/30)는 아직 안 준다. BE-1 settlement.py 지급 함수가 생기면 여기서 호출
        battle.status = BattleStatus.FINISHED
        session.add(battle)
        session.commit()
        session.refresh(battle)
    return battle


def _leaderboard(session: SessionDep, battle_id: uuid.UUID) -> list[LeaderboardEntry]:
    rows = session.exec(
        select(BattleRecord, User)
        .join(User, col(User.id) == col(BattleRecord.user_id))
        .where(BattleRecord.battle_id == battle_id)
        # 같은 dB면 먼저 도달한 사람이 위
        .order_by(col(BattleRecord.peak_db).desc(), col(BattleRecord.updated_at))
    ).all()
    return [
        LeaderboardEntry(
            rank=i + 1,
            user_id=user.id,
            nickname=user.display_nickname,
            peak_db=record.peak_db,
        )
        for i, (record, user) in enumerate(rows)
    ]


def _me(board: list[LeaderboardEntry], user_id: uuid.UUID) -> BattleMe:
    for e in board:
        if e.user_id == user_id:
            return BattleMe(rank=e.rank, peak_db=e.peak_db)
    return BattleMe()


def _state(session: SessionDep, battle: Battle, user_id: uuid.UUID) -> BattleState:
    board = _leaderboard(session, battle.id)
    remaining = 0
    if battle.status == BattleStatus.ONGOING and battle.ends_at:
        left = (battle.ends_at - datetime.now(UTC)).total_seconds()
        remaining = max(0, math.ceil(left))
    return BattleState(
        id=battle.id,
        community_id=battle.community_id,
        status=battle.status,
        remaining_sec=remaining,
        ends_at=battle.ends_at,
        max_players=battle.max_players,
        leaderboard=board,
        me=_me(board, user_id),
    )


@router.post("/communities/{id}/battles", response_model=BattleState)
def start_battle(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    body: BattleCreate | None = None,
) -> Any:
    """
    대결 시작. 이 커뮤니티에 진행 중인 대결이 있으면 새로 만들지 않고 그 대결을 돌려준다(다 같이 같은 대결에 참여).
    """
    if not session.get(Community, id):
        raise HTTPException(status_code=404, detail="Community not found")
    now = datetime.now(UTC)
    ongoing = session.exec(
        select(Battle).where(
            Battle.community_id == id,
            Battle.status == BattleStatus.ONGOING,
            col(Battle.ends_at) > now,
        )
    ).first()
    if ongoing:
        return _state(session, ongoing, current_user.id)

    duration = (body or BattleCreate()).duration_sec
    battle = Battle(
        community_id=id,
        status=BattleStatus.ONGOING,
        duration_sec=duration,
        started_at=now,
        ends_at=now + timedelta(seconds=duration),
    )
    session.add(battle)
    session.commit()
    session.refresh(battle)
    return _state(session, battle, current_user.id)


@router.get("/battles/{id}", response_model=BattleState)
def read_battle(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    대결 상태 폴링: status, 남은 시간, 리더보드, 내 순위.
    """
    return _state(session, _get_battle(session, id), current_user.id)


@router.post("/battles/{id}/records", response_model=BattleState)
def submit_record(
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    body: BattleRecordSubmit,
) -> Any:
    """
    측정 중 peak dB 제출. 측정하는 동안 계속 보내도 되고, 서버는 최댓값만 남긴다. 응답은 갱신된 대결 상태.
    """
    battle = _get_battle(session, id)
    if battle.status != BattleStatus.ONGOING:
        raise HTTPException(status_code=409, detail="Battle is not ongoing")

    joined = session.exec(
        select(BattleRecord.id).where(
            BattleRecord.battle_id == id, BattleRecord.user_id == current_user.id
        )
    ).first()
    if not joined:
        # shortcut: 동시에 처음 들어오는 요청끼리는 max_players를 1명 넘길 수 있다. 문제 되면 행 잠금
        count = session.exec(
            select(func.count()).where(BattleRecord.battle_id == id)
        ).one()
        if count >= battle.max_players:
            raise HTTPException(status_code=409, detail="Battle is full")

    now = datetime.now(UTC)
    stmt = insert(BattleRecord).values(
        id=uuid.uuid4(),
        battle_id=id,
        user_id=current_user.id,
        peak_db=body.peak_db,
        updated_at=now,
    )
    improved = stmt.excluded.peak_db > BattleRecord.peak_db
    session.execute(
        stmt.on_conflict_do_update(
            index_elements=["battle_id", "user_id"],
            set_={
                "peak_db": func.greatest(BattleRecord.peak_db, stmt.excluded.peak_db),
                "updated_at": case((improved, now), else_=BattleRecord.updated_at),
            },
        )
    )
    session.commit()
    return _state(session, battle, current_user.id)


@router.get("/battles/{id}/result", response_model=BattleResult)
def read_battle_result(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    종료 후 TOP3, 내 기록, 내 상위 %.
    """
    battle = _get_battle(session, id)
    if battle.status != BattleStatus.FINISHED:
        raise HTTPException(status_code=409, detail="Battle is not finished")
    board = _leaderboard(session, battle.id)
    me = _me(board, current_user.id)
    top = math.ceil(me.rank / len(board) * 100) if me.rank else None
    return BattleResult(
        id=battle.id,
        top3=board[:3],
        me=me,
        my_top_percent=top,
        participants=len(board),
    )
