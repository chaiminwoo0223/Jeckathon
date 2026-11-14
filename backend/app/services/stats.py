"""승률·요정 판정 (명세 §3.1, §3.2)과 응원 기록 집계. 정산 단계에서도 이 함수들을 쓴다."""

import uuid

from sqlmodel import Session, col, func, select

from app.models import (
    CheerRecord,
    CheerResult,
    FairyType,
    StatsPublic,
    Team,
    UserTeam,
)

VICTORY_WIN_RATE = 0.6  # 승률 이 값 이상이면 승리요정
DEFEAT_LOSE_RATE = 0.3  # 패배율 이 값 이상이면 패배요정 (승리요정이 우선)

_FAIRY_LABEL = {
    FairyType.VICTORY: "승리요정",
    FairyType.DEFEAT: "패배요정",
    FairyType.NEUTRAL: "중립요정",
}


def rates(win: int, lose: int) -> tuple[float, float]:
    """(승률, 패배율). 분모는 무승부를 뺀 승+패이고, 0이면 둘 다 0."""
    decided = win + lose
    if decided == 0:
        return 0.0, 0.0
    return win / decided, lose / decided


def fairy_type(win: int, lose: int) -> FairyType:
    win_rate, lose_rate = rates(win, lose)
    if win_rate >= VICTORY_WIN_RATE:
        return FairyType.VICTORY
    if lose_rate >= DEFEAT_LOSE_RATE:
        return FairyType.DEFEAT
    return FairyType.NEUTRAL


def fairy_label(fairy: FairyType, nickname: str) -> str:
    return f"{_FAIRY_LABEL[fairy]} {nickname}"


def build_stats(win: int, draw: int, lose: int) -> StatsPublic:
    win_rate, lose_rate = rates(win, lose)
    return StatsPublic(
        total=win + draw + lose,
        win=win,
        draw=draw,
        lose=lose,
        win_rate=round(win_rate, 2),
        lose_rate=round(lose_rate, 2),
    )


def users_stats(
    session: Session, user_ids: list[uuid.UUID]
) -> dict[uuid.UUID, StatsPublic]:
    """여러 유저의 통계를 쿼리 한 번으로 센다(확정된 기록만). 기록이 없으면 전부 0."""
    counts: dict[uuid.UUID, dict[CheerResult, int]] = {uid: {} for uid in user_ids}
    if user_ids:
        rows = session.exec(
            select(CheerRecord.user_id, CheerRecord.result, func.count())
            .where(
                col(CheerRecord.user_id).in_(user_ids),
                CheerRecord.result != CheerResult.PENDING,
            )
            .group_by(col(CheerRecord.user_id), col(CheerRecord.result))
        ).all()
        for uid, result, n in rows:
            counts[uid][CheerResult(result)] = n
    return {
        uid: build_stats(
            win=c.get(CheerResult.WIN, 0),
            draw=c.get(CheerResult.DRAW, 0),
            lose=c.get(CheerResult.LOSE, 0),
        )
        for uid, c in counts.items()
    }


def user_stats(session: Session, user_id: uuid.UUID) -> StatsPublic:
    """확정된 응원 기록(PENDING 제외)으로 승/무/패를 센다."""
    return users_stats(session, [user_id])[user_id]


def favorite_team(session: Session, user_id: uuid.UUID) -> Team | None:
    """최애팀: 가장 많이 응원한 팀(진행 전 기록 포함), 같으면 가장 최근에 응원한 팀.

    응원 기록이 없으면 응원팀 설정(UserTeam)에서 이름순 첫 팀, 그것도 없으면 None.
    """
    top = session.exec(
        select(CheerRecord.cheered_team_id)
        .where(CheerRecord.user_id == user_id)
        .group_by(col(CheerRecord.cheered_team_id))
        .order_by(func.count().desc(), func.max(CheerRecord.created_at).desc())
        .limit(1)
    ).first()
    if top is not None:
        return session.get(Team, top)
    return session.exec(
        select(Team)
        .join(UserTeam, col(UserTeam.team_id) == col(Team.id))
        .where(UserTeam.user_id == user_id)
        .order_by(col(Team.name))
        .limit(1)
    ).first()
