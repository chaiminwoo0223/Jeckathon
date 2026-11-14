import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col, select

from app.api.deps import CurrentUser, SessionDep, get_current_user
from app.api.routes.matches import KST, _kst_day_range, to_match_details
from app.models import (
    CheerRecord,
    CommunitiesMine,
    Community,
    CommunityBrief,
    CommunityInfo,
    CommunityMember,
    CommunityMemberPublic,
    CommunityMembersPublic,
    CommunityMineDay,
    CommunityMineItem,
    CommunityPublic,
    Match,
    MatchStatus,
    User,
)
from app.services import community as community_service
from app.services import stats as stats_service

router = APIRouter(prefix="/communities", tags=["communities"])
match_router = APIRouter(prefix="/matches", tags=["communities"])


def get_or_create_community(session: Session, match_id: uuid.UUID) -> Community:
    return community_service.get_or_create_communities(session, [match_id])[match_id]


def _info(
    session: Session, community: Community, match: Match, user_id: uuid.UUID
) -> CommunityInfo:
    opens_at, can_enter = community_service.enter_window(match)
    counts = community_service.member_counts(session, [community.id])
    joined = community.id in community_service.joined_ids(
        session, user_id, [community.id]
    )
    return CommunityInfo(
        id=community.id,
        match_id=community.match_id,
        member_count=counts.get(community.id, 0),
        joined=joined,
        enter_opens_at=opens_at,
        can_enter=can_enter,
    )


def _get_community(session: Session, id: uuid.UUID) -> tuple[Community, Match]:
    community = session.get(Community, id)
    match = session.get(Match, community.match_id) if community else None
    if not community or not match:
        raise HTTPException(status_code=404, detail="Community not found")
    return community, match


@router.get("/mine", response_model=CommunitiesMine)
def read_my_communities(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    내가 응원 신청한 경기(종료 전)를 KST 날짜별로 묶은 목록과 경기별 입장 가능 여부.
    신청한 경기가 없으면 `days`가 비어 있다(프론트가 캘린더로 보낸다).
    """
    rows = session.exec(
        select(CheerRecord, Match)
        .join(Match, col(Match.id) == col(CheerRecord.match_id))
        .where(
            CheerRecord.user_id == current_user.id,
            Match.status != MatchStatus.FINISHED,
        )
        .order_by(col(Match.kickoff_at))
    ).all()
    matches = [m for _, m in rows]
    communities = community_service.get_or_create_communities(
        session, [m.id for m in matches]
    )
    ids = [c.id for c in communities.values()]
    counts = community_service.member_counts(session, ids)
    joined = community_service.joined_ids(session, current_user.id, ids)

    now = datetime.now(UTC)
    grouped: dict[date, list[CommunityMineItem]] = defaultdict(list)
    for (record, match), detail in zip(
        rows, to_match_details(session, matches), strict=True
    ):
        community = communities[match.id]
        opens_at, can_enter = community_service.enter_window(match, now)
        grouped[match.kickoff_at.astimezone(KST).date()].append(
            CommunityMineItem(
                match=detail,
                cheered_team_id=record.cheered_team_id,
                community=CommunityBrief(
                    id=community.id,
                    member_count=counts.get(community.id, 0),
                    joined=community.id in joined,
                ),
                enter_opens_at=opens_at,
                can_enter=can_enter,
            )
        )
    return CommunitiesMine(
        server_now=now,
        count=len(rows),
        days=[CommunityMineDay(date=d, items=grouped[d]) for d in sorted(grouped)],
    )


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


@match_router.get("/{id}/community", response_model=CommunityInfo)
def read_match_community(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    경기별 커뮤니티 정보: 멤버 수, 내 입장 여부, 입장 가능 시각. 없으면 만든다.
    """
    match = session.get(Match, id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    community = get_or_create_community(session, id)
    return _info(session, community, match, current_user.id)


@router.post("/{id}/join", response_model=CommunityInfo)
def join_community(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    입장(초대장 → 입장). 응원 신청한 경기만, 경기 시작 1시간 전부터 종료 전까지 가능하다.
    이미 멤버면 그대로 성공한다.
    """
    community, match = _get_community(session, id)
    cheered = session.exec(
        select(CheerRecord.id).where(
            CheerRecord.user_id == current_user.id, CheerRecord.match_id == match.id
        )
    ).first()
    if not cheered:
        raise HTTPException(status_code=403, detail={"code": "NOT_CHEERED"})
    if match.status == MatchStatus.FINISHED:
        raise HTTPException(status_code=409, detail={"code": "MATCH_FINISHED"})
    opens_at, can_enter = community_service.enter_window(match)
    if not can_enter:
        raise HTTPException(
            status_code=403,
            detail={"code": "NOT_OPEN_YET", "enter_opens_at": opens_at.isoformat()},
        )
    session.execute(
        insert(CommunityMember)
        .values(
            community_id=community.id,
            user_id=current_user.id,
            joined_at=datetime.now(UTC),
        )
        .on_conflict_do_nothing(index_elements=["community_id", "user_id"])
    )
    session.commit()
    return _info(session, community, match, current_user.id)


@router.post("/{id}/leave", response_model=CommunityInfo)
def leave_community(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Any:
    """
    나가기. 멤버가 아니어도 성공한다.
    """
    community, match = _get_community(session, id)
    member = session.get(CommunityMember, (community.id, current_user.id))
    if member:
        session.delete(member)
        session.commit()
    return _info(session, community, match, current_user.id)


@router.get(
    "/{id}/members",
    response_model=CommunityMembersPublic,
    dependencies=[Depends(get_current_user)],
)
def read_community_members(session: SessionDep, id: uuid.UUID) -> Any:
    """
    멤버 목록: 닉네임·프로필 이미지·레벨·요정 타입. 입장 순.
    """
    community, _ = _get_community(session, id)
    rows = session.exec(
        select(CommunityMember, User)
        .join(User, col(User.id) == col(CommunityMember.user_id))
        .where(CommunityMember.community_id == community.id)
        .order_by(col(CommunityMember.joined_at), col(User.id))
    ).all()
    stats = stats_service.users_stats(session, [u.id for _, u in rows])
    data = []
    for member, user in rows:
        s = stats[user.id]
        fairy = stats_service.fairy_type(win=s.win, lose=s.lose)
        data.append(
            CommunityMemberPublic(
                user_id=user.id,
                nickname=user.display_nickname,
                profile_image_url=user.profile_image_url,
                level=user.level,
                fairy_type=fairy,
                fairy_label=stats_service.fairy_label(fairy, user.display_nickname),
                joined_at=member.joined_at,
            )
        )
    return CommunityMembersPublic(data=data, count=len(data))
