from sqlmodel import Session, create_engine, select

from app import crud
from app.core import security
from app.core.config import settings
from app.models import Badge, User, UserCreate, login_id_to_email
from app.seed.kbo import seed_kbo
from app.services.settlement import BADGES

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

    if settings.FASTAPI_ENV == "development":
        _seed_test_users(session)
    seed_kbo(session)
    _seed_badges(session)


def _seed_badges(session: Session) -> None:
    existing = set(session.exec(select(Badge.code)).all())
    for code, name, description in BADGES:
        if code not in existing:
            session.add(Badge(code=code, name=name, description=description))
    session.commit()


# 로컬 개발 전용 아이디 로그인 테스트 계정(be1/login-page에서 옮김). 운영 배포는 FASTAPI_ENV가 없어 넣지 않는다
TEST_USER_PASSWORD = "cheer1234"
TEST_USERS = [
    ("test1", "뚜비응원단"),
    ("test2", "민지"),
    ("test3", "아쉬운토끼"),
    ("test4", "직관러"),
    ("test5", "응원단장"),
]


def _seed_test_users(session: Session) -> None:
    for username, nickname in TEST_USERS:
        email = login_id_to_email(username)
        if session.exec(select(User.id).where(User.email == email)).first():
            continue
        session.add(
            User(
                email=email,
                nickname=nickname,
                hashed_password=security.get_password_hash(TEST_USER_PASSWORD),
            )
        )
    session.commit()
