from datetime import UTC, datetime, timedelta

from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import Match, MatchStatus, Team, User, UserCreate

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)

    _seed_teams_and_matches(session)


def _seed_teams_and_matches(session: Session) -> None:
    if session.exec(select(Team)).first() is not None:
        return

    league = "KBO리그"
    teams = {
        name: Team(name=name, full_name=full_name, league=league)
        for name, full_name in [
            ("LG", "LG 트윈스"),
            ("두산", "두산 베어스"),
            ("KIA", "KIA 타이거즈"),
            ("삼성", "삼성 라이온즈"),
            ("롯데", "롯데 자이언츠"),
            ("한화", "한화 이글스"),
        ]
    }
    session.add_all(teams.values())
    session.commit()

    now = datetime.now(UTC)
    today_kickoff = now + timedelta(hours=1)  # 오늘 경기: 데모 때 항상 당일
    fixtures = [
        ("LG", "두산", today_kickoff, MatchStatus.SCHEDULED, None, None),
        (
            "KIA",
            "삼성",
            today_kickoff + timedelta(hours=2),
            MatchStatus.SCHEDULED,
            None,
            None,
        ),
        ("롯데", "한화", now - timedelta(days=3), MatchStatus.FINISHED, 5, 3),
        ("두산", "KIA", now - timedelta(days=7), MatchStatus.FINISHED, 2, 7),
        (
            "삼성",
            "LG",
            now + timedelta(days=5),
            MatchStatus.SCHEDULED,
            None,
            None,
        ),
    ]
    for home, away, kickoff, status, home_score, away_score in fixtures:
        session.add(
            Match(
                home_team_id=teams[home].id,
                away_team_id=teams[away].id,
                league=league,
                kickoff_at=kickoff,
                status=status,
                home_score=home_score,
                away_score=away_score,
                finished_at=(kickoff + timedelta(hours=3))
                if status == MatchStatus.FINISHED
                else None,
            )
        )
    session.commit()
