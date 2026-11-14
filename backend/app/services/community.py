"""커뮤니티 입장 규칙(명세 §4.4)과 공용 조회.

입장은 경기 시작 3시간 전부터 경기 종료까지이고, 응원 신청한 경기만 가능하다.
경기 상태는 자동으로 LIVE가 되지 않으므로(스케줄러 없음) 상태가 아니라 시간으로 판단한다.
`/communities/mine`, `/matches/{id}/community`, `join`이 모두 이 규칙 한 곳을 쓴다.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col, func, select

from app.models import Community, CommunityMember, Match, MatchStatus

ENTER_LEAD = timedelta(hours=3)


def enter_window(match: Match, now: datetime | None = None) -> tuple[datetime, bool]:
    """(입장 시작 시각, 지금 입장 가능한가). 테스트에서 now를 넣을 수 있다."""
    now = now or datetime.now(UTC)
    opens_at = match.kickoff_at - ENTER_LEAD
    return opens_at, now >= opens_at and match.status != MatchStatus.FINISHED


def get_or_create_communities(
    session: Session, match_ids: list[uuid.UUID]
) -> dict[uuid.UUID, Community]:
    """경기별 커뮤니티를 돌려주고 없으면 만든다. 동시에 만들어도 경기당 하나만 남는다."""
    if not match_ids:
        return {}
    session.execute(
        insert(Community)
        .values(
            [
                {"id": uuid.uuid4(), "match_id": m, "created_at": datetime.now(UTC)}
                for m in match_ids
            ]
        )
        .on_conflict_do_nothing(index_elements=["match_id"])
    )
    session.commit()
    rows = session.exec(
        select(Community).where(col(Community.match_id).in_(match_ids))
    ).all()
    return {c.match_id: c for c in rows}


def member_counts(
    session: Session, community_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    if not community_ids:
        return {}
    rows = session.exec(
        select(CommunityMember.community_id, func.count())
        .where(col(CommunityMember.community_id).in_(community_ids))
        .group_by(col(CommunityMember.community_id))
    ).all()
    return dict(rows)


def joined_ids(
    session: Session, user_id: uuid.UUID, community_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    if not community_ids:
        return set()
    return set(
        session.exec(
            select(CommunityMember.community_id).where(
                CommunityMember.user_id == user_id,
                col(CommunityMember.community_id).in_(community_ids),
            )
        ).all()
    )
