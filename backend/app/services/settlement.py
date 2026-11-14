"""경기 종료 정산: 포인트 지급(명세 §3.3), 레벨(§3.4), 배지(§3.5).

포인트 지급은 `grant_points` 한 곳에서만 한다. 대결 TOP3 지급(BE-2)도 이 함수를 호출한다.
이 모듈의 함수는 커밋하지 않는다. 호출자가 한 트랜잭션으로 묶어 커밋한다.
"""

import uuid
from datetime import UTC, datetime

from sqlmodel import Session, col, select

from app.models import (
    Badge,
    CheerRecord,
    CheerResult,
    Match,
    MatchStatus,
    PointReason,
    PointTransaction,
    User,
    UserBadge,
)
from app.services import stats as stats_service

MATCH_RESULT_POINTS = {
    CheerResult.WIN: 100,
    CheerResult.DRAW: 50,
    CheerResult.LOSE: 30,
}
DECIBEL_TOP3_POINTS = (100, 50, 30)  # 1·2·3등 (BE-2의 대결 정산이 사용)
POINTS_PER_LEVEL = 300
WIN_STREAK_TARGET = 3
STEADY_FAN_MATCHES = 10
DECIBEL_MASTER_DB = 110.0

# 시드 대상 배지 (명세 §3.5)
BADGES: list[tuple[str, str, str]] = [
    ("VICTORY_FAIRY", "승리요정", "승률 60% 이상"),
    ("DEFEAT_FAIRY", "패배요정", "패배율 30% 이상"),
    ("WIN_STREAK_3", "연승러", "3연승"),
    ("DECIBEL_MASTER", "데시벨 마스터", "최고 측정 110dB 이상"),
    ("STEADY_FAN", "꾸준한 응원단", "10경기 이상 기록"),
]


def level_for(total_points: int) -> int:
    return total_points // POINTS_PER_LEVEL + 1


def grant_points(
    session: Session,
    user_id: uuid.UUID,
    amount: int,
    reason: PointReason,
    related_id: str | None = None,
) -> PointTransaction:
    """포인트 내역을 남기고 total_points·level을 갱신한다. 커밋은 호출자가 한다.

    유저 행을 잠가서 정산과 대결 지급이 동시에 와도 합계가 어긋나지 않는다.
    같은 (유저, 사유, related_id)를 두 번 지급하면 flush에서 unique 위반(IntegrityError)이 난다.
    """
    user = session.exec(select(User).where(User.id == user_id).with_for_update()).one()
    user.total_points += amount
    user.level = level_for(user.total_points)
    tx = PointTransaction(
        user_id=user_id, amount=amount, reason=reason, related_id=related_id
    )
    session.add_all([user, tx])
    session.flush()
    return tx


def result_for(cheered_home: bool, home_score: int, away_score: int) -> CheerResult:
    """응원팀 기준의 결과."""
    if home_score == away_score:
        return CheerResult.DRAW
    home_won = home_score > away_score
    return CheerResult.WIN if home_won == cheered_home else CheerResult.LOSE


def _has_win_streak(session: Session, user_id: uuid.UUID) -> bool:
    """확정된 기록을 경기 시작 시각 최신순으로 봤을 때 앞의 3건이 모두 승리인가."""
    recent = session.exec(
        select(CheerRecord.result)
        .join(Match, col(Match.id) == col(CheerRecord.match_id))
        .where(
            CheerRecord.user_id == user_id, CheerRecord.result != CheerResult.PENDING
        )
        .order_by(col(Match.kickoff_at).desc())
        .limit(WIN_STREAK_TARGET)
    ).all()
    return len(recent) == WIN_STREAK_TARGET and all(
        r == CheerResult.WIN for r in recent
    )


def evaluate_badges(
    session: Session, user_id: uuid.UUID, peak_db: float | None = None
) -> list[str]:
    """조건을 채운 배지를 지급하고, 이번에 새로 얻은 배지 code 목록을 돌려준다.

    한 번 얻은 배지는 회수하지 않는다. `peak_db`는 대결 종료 후 BE-2가 그 유저의 최고 측정값을 넘긴다.
    """
    stats = stats_service.user_stats(session, user_id)
    win_rate, lose_rate = stats_service.rates(stats.win, stats.lose)
    earned = {
        "VICTORY_FAIRY": win_rate >= stats_service.VICTORY_WIN_RATE,
        "DEFEAT_FAIRY": lose_rate >= stats_service.DEFEAT_LOSE_RATE,
        "WIN_STREAK_3": _has_win_streak(session, user_id),
        "STEADY_FAN": stats.total >= STEADY_FAN_MATCHES,
        "DECIBEL_MASTER": peak_db is not None and peak_db >= DECIBEL_MASTER_DB,
    }
    codes = [code for code, ok in earned.items() if ok]
    if not codes:
        return []
    badges = session.exec(select(Badge).where(col(Badge.code).in_(codes))).all()
    owned = set(
        session.exec(
            select(UserBadge.badge_id).where(UserBadge.user_id == user_id)
        ).all()
    )
    new_codes: list[str] = []
    for badge in badges:
        if badge.id not in owned:
            session.add(UserBadge(user_id=user_id, badge_id=badge.id))
            new_codes.append(badge.code)
    session.flush()
    return new_codes


def settle_match(
    session: Session, match: Match, home_score: int, away_score: int
) -> dict[CheerResult, int]:
    """경기를 종료하고 PENDING 응원 기록을 확정해 포인트·배지를 지급한다.

    돌려주는 값은 결과별 확정 건수다. 커밋은 호출자가 한다.
    """
    match.status = MatchStatus.FINISHED
    match.home_score = home_score
    match.away_score = away_score
    match.finished_at = datetime.now(UTC)
    session.add(match)

    counts = {CheerResult.WIN: 0, CheerResult.DRAW: 0, CheerResult.LOSE: 0}
    # 유저 id 순으로 처리해 동시 정산끼리 잠금 순서가 같게 한다(데드락 방지).
    records = session.exec(
        select(CheerRecord)
        .where(
            CheerRecord.match_id == match.id, CheerRecord.result == CheerResult.PENDING
        )
        .order_by(col(CheerRecord.user_id))
    ).all()
    for record in records:
        record.result = result_for(
            record.cheered_team_id == match.home_team_id, home_score, away_score
        )
        record.points_earned = MATCH_RESULT_POINTS[record.result]
        session.add(record)
        counts[record.result] += 1
        grant_points(
            session,
            record.user_id,
            record.points_earned,
            PointReason.MATCH_RESULT,
            related_id=str(match.id),
        )
    session.flush()  # 배지 평가가 방금 확정한 기록을 읽는다
    for record in records:
        evaluate_badges(session, record.user_id)
    return counts
