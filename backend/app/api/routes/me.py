import uuid
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.api.routes.matches import to_match_details
from app.models import (
    CheerRecord,
    CheerRecordItem,
    CheerRecordsPublic,
    Match,
    MeProfile,
    MeSummary,
    ProfileUpdate,
    ShareCard,
    StatsPublic,
    Team,
    TeamPublic,
    TeamsPublic,
    User,
    UserSetting,
    UserSettingPublic,
    UserSettingUpdate,
    UserTeam,
    UserTeamAdd,
)
from app.services import stats as stats_service

router = APIRouter(prefix="/me", tags=["me"])


def to_profile(user: User) -> MeProfile:
    return MeProfile(
        id=user.id,
        nickname=user.display_nickname,
        bio=user.bio,
        profile_image_url=user.profile_image_url,
        level=user.level,
        total_points=user.total_points,
    )


def _my_teams(session: Session, user: User) -> TeamsPublic:
    teams = session.exec(
        select(Team)
        .join(UserTeam, col(UserTeam.team_id) == col(Team.id))
        .where(UserTeam.user_id == user.id)
        .order_by(col(Team.name))
    ).all()
    return TeamsPublic(
        data=[TeamPublic.model_validate(t) for t in teams], count=len(teams)
    )


def _get_or_create_setting(session: Session, user: User) -> UserSetting:
    setting = session.get(UserSetting, user.id)
    if setting is None:
        setting = UserSetting(user_id=user.id)
        session.add(setting)
        session.commit()
        session.refresh(setting)
    return setting


@router.get("", response_model=MeSummary)
def read_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    내 프로필 + 통계 요약. 통계는 확정된 응원 기록(PENDING 제외)으로 센다.
    """
    stats = stats_service.user_stats(session, current_user.id)
    fairy = stats_service.fairy_type(win=stats.win, lose=stats.lose)
    return MeSummary(
        **to_profile(current_user).model_dump(),
        fairy_type=fairy,
        fairy_label=stats_service.fairy_label(fairy, current_user.display_nickname),
        stats=stats,
        teams=_my_teams(session, current_user).data,
    )


@router.get("/records", response_model=CheerRecordsPublic)
def read_my_records(
    session: SessionDep,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> Any:
    """
    내 응원 기록. 최근 경기 순, 1부터 시작하는 page.
    """
    where = CheerRecord.user_id == current_user.id
    count = session.exec(
        select(func.count()).select_from(CheerRecord).where(where)
    ).one()
    rows = session.exec(
        select(CheerRecord, Match)
        .join(Match, col(Match.id) == col(CheerRecord.match_id))
        .where(where)
        .order_by(col(Match.kickoff_at).desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    details = to_match_details(session, [m for _, m in rows])
    items = [
        CheerRecordItem(**record.model_dump(), match=detail)
        for (record, _), detail in zip(rows, details, strict=True)
    ]
    return CheerRecordsPublic(data=items, count=count, page=page, size=size)


@router.get("/stats", response_model=StatsPublic)
def read_my_stats(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    시즌 통계(도넛용): 승/무/패 수와 승률·패배율. 진행 전(PENDING) 기록은 세지 않는다.
    """
    return stats_service.user_stats(session, current_user.id)


@router.get("/share-card", response_model=ShareCard)
def read_share_card(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    SNS 공유 카드 데이터: 닉네임, 요정, 승률·경기수, 최애팀.
    """
    stats = stats_service.user_stats(session, current_user.id)
    fairy = stats_service.fairy_type(win=stats.win, lose=stats.lose)
    team = stats_service.favorite_team(session, current_user.id)
    nickname = current_user.display_nickname
    return ShareCard(
        nickname=nickname,
        profile_image_url=current_user.profile_image_url,
        fairy_type=fairy,
        fairy_label=stats_service.fairy_label(fairy, nickname),
        stats=stats,
        favorite_team=TeamPublic.model_validate(team) if team else None,
    )


@router.patch("/profile", response_model=MeProfile)
def update_profile(
    session: SessionDep, current_user: CurrentUser, profile_in: ProfileUpdate
) -> Any:
    """
    닉네임·한 줄 소개·프로필 이미지 수정. 보내지 않은 필드는 그대로 둔다.
    """
    data = profile_in.model_dump(exclude_unset=True)
    # 닉네임·소개는 비울 수 없다. null은 "변경 없음"으로 본다. 이미지 URL만 null로 지울 수 있다.
    for key in ("nickname", "bio"):
        if data.get(key) is None:
            data.pop(key, None)
    current_user.sqlmodel_update(data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return to_profile(current_user)


@router.get("/settings", response_model=UserSettingPublic)
def read_settings(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    설정 조회. 한 번도 저장한 적 없으면 기본값으로 만들어 돌려준다.
    """
    return _get_or_create_setting(session, current_user)


@router.patch("/settings", response_model=UserSettingPublic)
def update_settings(
    session: SessionDep, current_user: CurrentUser, settings_in: UserSettingUpdate
) -> Any:
    """
    설정 토글 일부 업데이트.
    """
    setting = _get_or_create_setting(session, current_user)
    data = settings_in.model_dump(exclude_unset=True, exclude_none=True)
    setting.sqlmodel_update(data)
    session.add(setting)
    session.commit()
    session.refresh(setting)
    return setting


@router.get("/teams", response_model=TeamsPublic)
def read_my_teams(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    응원하는 팀 목록.
    """
    return _my_teams(session, current_user)


@router.post("/teams", response_model=TeamsPublic)
def add_my_team(
    session: SessionDep, current_user: CurrentUser, team_in: UserTeamAdd
) -> Any:
    """
    응원팀 추가. 이미 추가한 팀이면 그대로 둔다. 갱신된 목록을 돌려준다.
    """
    if session.get(Team, team_in.team_id) is None:
        raise HTTPException(status_code=404, detail="Team not found")
    if session.get(UserTeam, (current_user.id, team_in.team_id)) is None:
        session.add(UserTeam(user_id=current_user.id, team_id=team_in.team_id))
        session.commit()
    return _my_teams(session, current_user)


@router.delete("/teams/{team_id}", response_model=TeamsPublic)
def remove_my_team(
    session: SessionDep, current_user: CurrentUser, team_id: uuid.UUID
) -> Any:
    """
    응원팀 제거. 갱신된 목록을 돌려준다.
    """
    link = session.get(UserTeam, (current_user.id, team_id))
    if link is None:
        raise HTTPException(status_code=404, detail="Team not in my teams")
    session.delete(link)
    session.commit()
    return _my_teams(session, current_user)
