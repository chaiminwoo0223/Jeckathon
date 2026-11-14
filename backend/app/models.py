import enum
import uuid
from datetime import UTC, datetime
from datetime import date as date_type
from typing import Annotated

from pydantic import EmailStr, StringConstraints
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(UTC)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)


# Properties to receive via API on update, all are optional
class UserUpdate(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(default_factory=get_datetime_utc)
    items: list[Item] = Relationship(back_populates="owner", cascade_delete=True)
    # CHEER 101 (BE-1). 기존 행이 있으므로 server_default가 필요하다.
    nickname: str = Field(
        default="", max_length=50, sa_column_kwargs={"server_default": ""}
    )
    bio: str = Field(
        default="", max_length=200, sa_column_kwargs={"server_default": ""}
    )
    profile_image_url: str | None = Field(default=None, max_length=500)
    level: int = Field(default=1, sa_column_kwargs={"server_default": "1"})
    total_points: int = Field(default=0, sa_column_kwargs={"server_default": "0"})

    @property
    def display_nickname(self) -> str:
        """닉네임이 비어 있으면(관리자 등) 이메일 앞부분을 쓴다."""
        return self.nickname or self.email.split("@")[0]


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(SQLModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(default_factory=get_datetime_utc)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


# --- BE-1 ---
class MatchStatus(enum.StrEnum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINISHED = "FINISHED"


class TeamBase(SQLModel):
    name: str = Field(max_length=100)  # "LG"
    full_name: str = Field(max_length=255)  # "LG 트윈스"
    logo_url: str = Field(default="", max_length=500)
    league: str = Field(max_length=100)  # "KBO리그"


class Team(TeamBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class TeamPublic(TeamBase):
    id: uuid.UUID


class TeamsPublic(SQLModel):
    data: list[TeamPublic]
    count: int


class MatchBase(SQLModel):
    league: str = Field(max_length=100)
    kickoff_at: datetime = Field(sa_type=DateTime(timezone=True))  # type: ignore
    status: MatchStatus = Field(default=MatchStatus.SCHEDULED)
    home_score: int | None = None  # 종료 시 채워짐
    away_score: int | None = None
    finished_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class Match(MatchBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    home_team_id: uuid.UUID = Field(foreign_key="team.id", nullable=False, index=True)
    away_team_id: uuid.UUID = Field(foreign_key="team.id", nullable=False, index=True)


class MatchPublic(MatchBase):
    id: uuid.UUID
    home_team_id: uuid.UUID
    away_team_id: uuid.UUID


class MatchesPublic(SQLModel):
    data: list[MatchPublic]
    count: int


class MatchDetail(MatchPublic):
    """팀 정보를 풀어 담은 경기 응답 (화면이 팀명·로고를 바로 그린다)."""

    home_team: TeamPublic
    away_team: TeamPublic


class MatchDay(SQLModel):
    date: date_type  # KST 기준 날짜
    matches: list[MatchDetail]


class MatchesByMonth(SQLModel):
    month: str  # "YYYY-MM"
    days: list[MatchDay]  # 경기가 있는 날만, 날짜 오름차순
    count: int


class MatchesToday(SQLModel):
    date: date_type
    data: list[MatchDetail]
    count: int


class UserSettingBase(SQLModel):
    notify_match_schedule: bool = True  # 경기 일정 알림
    notify_community_invite: bool = True  # 커뮤니티 초대 알림
    notify_ranking_reward: bool = True  # 랭킹/보상 알림
    notify_service: bool = False  # 서비스 소식/이벤트
    auto_join_community: bool = True  # 경기 당일 자동 입장
    mic_permission: bool = False  # 데시벨 마이크 권한
    ranking_public: bool = True  # 랭킹 공개 여부


class UserSetting(UserSettingBase, table=True):
    user_id: uuid.UUID = Field(
        foreign_key="user.id", primary_key=True, ondelete="CASCADE"
    )


class UserSettingPublic(UserSettingBase):
    pass


class UserSettingUpdate(SQLModel):
    notify_match_schedule: bool | None = None
    notify_community_invite: bool | None = None
    notify_ranking_reward: bool | None = None
    notify_service: bool | None = None
    auto_join_community: bool | None = None
    mic_permission: bool | None = None
    ranking_public: bool | None = None


class UserTeam(SQLModel, table=True):
    """응원하는 팀 (User : Team = M : N)."""

    user_id: uuid.UUID = Field(
        foreign_key="user.id", primary_key=True, ondelete="CASCADE"
    )
    team_id: uuid.UUID = Field(
        foreign_key="team.id", primary_key=True, ondelete="CASCADE"
    )


class UserTeamAdd(SQLModel):
    team_id: uuid.UUID


class ProfileUpdate(SQLModel):
    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    bio: str | None = Field(default=None, max_length=200)
    profile_image_url: str | None = Field(default=None, max_length=500)


class FairyType(enum.StrEnum):
    VICTORY = "VICTORY"
    DEFEAT = "DEFEAT"
    NEUTRAL = "NEUTRAL"


class StatsPublic(SQLModel):
    total: int
    win: int
    draw: int
    lose: int
    win_rate: float
    lose_rate: float


class MeProfile(SQLModel):
    id: uuid.UUID
    nickname: str
    bio: str
    profile_image_url: str | None
    level: int
    total_points: int


class MeSummary(MeProfile):
    fairy_type: FairyType
    fairy_label: str
    stats: StatsPublic
    teams: list[TeamPublic]


USERNAME_PATTERN = r"^[A-Za-z0-9_]{4,20}$"
LOGIN_ID_DOMAIN = (
    "users.cheer101.example.com"  # 예약 도메인: 메일이 실제로 나가지 않는다
)


def login_id_to_email(login_id: str) -> str:
    """로그인 아이디는 별도 칼럼 없이 email 칼럼에 합성해 저장한다(대소문자 구분 없음)."""
    return f"{login_id.lower()}@{LOGIN_ID_DOMAIN}"


Username = Annotated[str, StringConstraints(pattern=USERNAME_PATTERN)]


class AuthCredentials(SQLModel):
    """가입·로그인 공용. 아이디는 영문·숫자·밑줄 4~20자이고 대소문자를 구분하지 않는다."""

    username: Username
    password: str = Field(min_length=4, max_length=128)


class AuthResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    user: MeProfile


class UsernameCheck(SQLModel):
    username: str
    available: bool
