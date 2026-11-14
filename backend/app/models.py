import enum
import uuid
from datetime import UTC, datetime
from datetime import date as date_type
from typing import Annotated

from pydantic import EmailStr, StringConstraints
from sqlalchemy import DateTime, UniqueConstraint
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
    # 화면 TeamLogo가 로고 대신 그리는 약어·팀 컬러
    short_name: str = Field(
        default="", max_length=10, sa_column_kwargs={"server_default": ""}
    )  # "LG"
    color: str = Field(
        default="", max_length=20, sa_column_kwargs={"server_default": ""}
    )  # "#C30452"


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
    venue: str = Field(
        default="", max_length=50, sa_column_kwargs={"server_default": ""}
    )  # "잠실"
    round_label: str = Field(
        default="", max_length=50, sa_column_kwargs={"server_default": ""}
    )  # 포스트시즌만: "KS 5차전"


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


# --- BE-2 ---
class Community(SQLModel, table=True):
    """경기 1개당 1개 응원방."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    match_id: uuid.UUID = Field(foreign_key="match.id", unique=True, nullable=False)
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class CommunityPublic(SQLModel):
    id: uuid.UUID
    match_id: uuid.UUID
    created_at: datetime


class CommunityMember(SQLModel, table=True):
    community_id: uuid.UUID = Field(
        foreign_key="community.id", primary_key=True, ondelete="CASCADE"
    )
    user_id: uuid.UUID = Field(
        foreign_key="user.id", primary_key=True, ondelete="CASCADE"
    )
    joined_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class CommunityInfo(SQLModel):
    """경기별 커뮤니티와 내 입장 상태. 초대장 화면이 쓴다."""

    id: uuid.UUID
    match_id: uuid.UUID
    member_count: int
    joined: bool
    enter_opens_at: datetime  # 경기 시작 3시간 전
    can_enter: bool  # 서버 시각 기준 지금 입장 가능한가


class CommunityBrief(SQLModel):
    id: uuid.UUID
    member_count: int
    joined: bool


class CommunityMineItem(SQLModel):
    match: MatchDetail
    cheered_team_id: uuid.UUID
    community: CommunityBrief
    enter_opens_at: datetime
    can_enter: bool


class CommunityMineDay(SQLModel):
    date: date_type  # KST 기준 날짜
    items: list[CommunityMineItem]


class CommunitiesMine(SQLModel):
    server_now: datetime  # 프론트가 카운트다운을 그릴 때 쓰는 서버 시각
    count: int
    days: list[CommunityMineDay]  # 날짜 오름차순, 비어 있으면 신청한 경기가 없다


class CommunityMemberPublic(SQLModel):
    user_id: uuid.UUID
    nickname: str
    profile_image_url: str | None
    level: int
    fairy_type: FairyType
    fairy_label: str
    joined_at: datetime


class CommunityMembersPublic(SQLModel):
    data: list[CommunityMemberPublic]
    count: int


class BattleStatus(enum.StrEnum):
    WAITING = "WAITING"
    ONGOING = "ONGOING"
    FINISHED = "FINISHED"


class Battle(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    community_id: uuid.UUID = Field(
        foreign_key="community.id", nullable=False, index=True
    )
    status: BattleStatus = Field(default=BattleStatus.WAITING)
    duration_sec: int = 60
    max_players: int = 5
    started_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    ends_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class BattleRecord(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("battle_id", "user_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    battle_id: uuid.UUID = Field(
        foreign_key="battle.id", nullable=False, ondelete="CASCADE"
    )
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    peak_db: float  # 유저별 최고값, 제출할 때마다 max 유지
    updated_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class BattleCreate(SQLModel):
    duration_sec: int = Field(default=60, ge=5, le=600)


class BattleRecordSubmit(SQLModel):
    # Web Audio 게임용 dB(명세 §0). 실제 SPL 아님
    peak_db: float = Field(ge=0, le=200)


class LeaderboardEntry(SQLModel):
    rank: int
    user_id: uuid.UUID
    nickname: str
    peak_db: float


class BattleMe(SQLModel):
    rank: int | None = None  # 아직 제출 안 했으면 None
    peak_db: float | None = None


class BattleState(SQLModel):
    id: uuid.UUID
    community_id: uuid.UUID
    status: BattleStatus
    remaining_sec: int
    ends_at: datetime | None
    max_players: int
    leaderboard: list[LeaderboardEntry]
    me: BattleMe


class BattleTopEntry(LeaderboardEntry):
    points: int  # 이 대결로 받은 포인트(100/50/30)


class BattleResult(SQLModel):
    id: uuid.UUID
    top3: list[BattleTopEntry]
    me: BattleMe
    my_top_percent: int | None = None  # 상위 몇 %인지, 미참여면 None
    participants: int
    my_points: int = 0  # 내가 이 대결로 받은 포인트, TOP3 밖이면 0


class CheerResult(enum.StrEnum):
    PENDING = "PENDING"  # 경기 종료 전
    WIN = "WIN"
    DRAW = "DRAW"
    LOSE = "LOSE"


class CheerRecord(SQLModel, table=True):
    """응원 기록. 유저는 한 경기에 한 번만 응원팀을 고른다."""

    __table_args__ = (UniqueConstraint("user_id", "match_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, index=True, ondelete="CASCADE"
    )
    match_id: uuid.UUID = Field(
        foreign_key="match.id", nullable=False, index=True, ondelete="CASCADE"
    )
    cheered_team_id: uuid.UUID = Field(foreign_key="team.id", nullable=False)
    result: CheerResult = Field(default=CheerResult.PENDING)
    points_earned: int = 0
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class CheerIn(SQLModel):
    cheered_team_id: uuid.UUID


class CheerRecordPublic(SQLModel):
    id: uuid.UUID
    match_id: uuid.UUID
    cheered_team_id: uuid.UUID
    result: CheerResult
    points_earned: int
    created_at: datetime


class CheerRecordItem(CheerRecordPublic):
    match: MatchDetail  # 목록 화면이 경기·팀 정보를 바로 그린다


class CheerRecordsPublic(SQLModel):
    data: list[CheerRecordItem]
    count: int  # 전체 기록 수
    page: int
    size: int


class Badge(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=50)  # "VICTORY_FAIRY"
    name: str = Field(max_length=100)  # "승리요정"
    description: str = Field(max_length=255)  # "승률 60% 이상"
    icon_url: str = Field(default="", max_length=500)


class UserBadge(SQLModel, table=True):
    user_id: uuid.UUID = Field(
        foreign_key="user.id", primary_key=True, ondelete="CASCADE"
    )
    badge_id: uuid.UUID = Field(
        foreign_key="badge.id", primary_key=True, ondelete="CASCADE"
    )
    acquired_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class PointReason(enum.StrEnum):
    MATCH_RESULT = "MATCH_RESULT"
    DECIBEL_TOP3 = "DECIBEL_TOP3"


class PointTransaction(SQLModel, table=True):
    """포인트 내역. 같은 (유저, 사유, 대상)에는 한 번만 지급한다."""

    __table_args__ = (UniqueConstraint("user_id", "reason", "related_id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, index=True, ondelete="CASCADE"
    )
    amount: int  # +100, +50, +30 ...
    reason: PointReason
    related_id: str | None = Field(default=None, max_length=64)  # matchId or battleId
    created_at: datetime = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),
    )


class MatchFinishIn(SQLModel):
    home_score: int = Field(ge=0)
    away_score: int = Field(ge=0)


class MatchFinishOut(SQLModel):
    match: MatchDetail
    settled: int  # 이번에 확정된 응원 기록 수
    win: int
    draw: int
    lose: int


class ShareCard(SQLModel):
    """SNS 공유 카드에 그리는 값. 이미지는 프론트가 만든다."""

    nickname: str
    profile_image_url: str | None
    fairy_type: FairyType
    fairy_label: str
    stats: StatsPublic  # total이 경기수
    favorite_team: TeamPublic | None


# --- BE-2 (보상 조회) ---
class PointTransactionPublic(SQLModel):
    id: uuid.UUID
    amount: int
    reason: PointReason
    related_id: str | None  # MATCH_RESULT면 matchId, DECIBEL_TOP3면 battleId
    created_at: datetime


class PointsPublic(SQLModel):
    data: list[PointTransactionPublic]
    count: int  # 전체 내역 수
    page: int
    size: int
    total_points: int


class UserBadgePublic(SQLModel):
    code: str
    name: str
    description: str
    icon_url: str
    acquired_at: datetime


class UserBadgesPublic(SQLModel):
    data: list[UserBadgePublic]
    count: int
