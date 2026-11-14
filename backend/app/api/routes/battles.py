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
    BattleTopEntry,
    Community,
    LeaderboardEntry,
    PointReason,
    PointTransaction,
    User,
)
from app.services import settlement

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
        _finish(session, battle.id)
    return battle


def _finish(session: SessionDep, battle_id: uuid.UUID) -> None:
    """종료 전환 + TOP3 포인트 + 데시벨 배지를 한 트랜잭션으로 한다.

    대결 행을 잠그고 다시 읽어서, 동시에 폴링해도 ONGOING을 본 한 요청만 정산한다.
    """
    battle = session.exec(
        select(Battle)
        .where(Battle.id == battle_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    if battle.status != BattleStatus.ONGOING:
        session.commit()  # 다른 요청이 이미 정산함. 잠금만 푼다
        return
    battle.status = BattleStatus.FINISHED
    session.add(battle)
    # shortcut: 종료 직전에 상태 검사를 통과한 기록 제출이 정산 뒤에 들어올 수 있다(지급엔 반영 안 됨). 문제 되면 submit_record에서도 행 잠금
    board = _leaderboard(session, battle.id)
    top3 = zip(board, settlement.DECIBEL_TOP3_POINTS, strict=False)
    # 유저 id 순으로 지급해 경기 정산과 잠금 순서를 맞춘다(데드락 방지)
    for entry, points in sorted(top3, key=lambda t: t[0].user_id):
        settlement.grant_points(
            session,
            entry.user_id,
            points,
            PointReason.DECIBEL_TOP3,
            related_id=str(battle.id),
        )
    for entry in board:
        settlement.evaluate_badges(session, entry.user_id, peak_db=entry.peak_db)
    session.commit()


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
    종료 후 TOP3(받은 포인트 포함), 내 기록, 내 상위 %, 내가 받은 포인트.
    """
    battle = _get_battle(session, id)
    if battle.status != BattleStatus.FINISHED:
        raise HTTPException(status_code=409, detail="Battle is not finished")
    board = _leaderboard(session, battle.id)
    me = _me(board, current_user.id)
    top = math.ceil(me.rank / len(board) * 100) if me.rank else None
    # 실제 지급 내역에서 읽는다(순위로 다시 계산하지 않음)
    paid = dict(
        session.exec(
            select(PointTransaction.user_id, PointTransaction.amount).where(
                PointTransaction.reason == PointReason.DECIBEL_TOP3,
                PointTransaction.related_id == str(battle.id),
            )
        ).all()
    )
    return BattleResult(
        id=battle.id,
        top3=[
            BattleTopEntry(**e.model_dump(), points=paid.get(e.user_id, 0))
            for e in board[:3]
        ],
        me=me,
        my_top_percent=top,
        participants=len(board),
        my_points=paid.get(current_user.id, 0),
    )
