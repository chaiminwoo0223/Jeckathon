from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from app import crud
from app.api.deps import CurrentUser, SessionDep, get_current_active_superuser
from app.api.routes.me import to_profile
from app.core import security
from app.core.config import settings
from app.models import (
    USERNAME_PATTERN,
    AuthCredentials,
    AuthResponse,
    Message,
    NewPassword,
    Token,
    User,
    UsernameCheck,
    UserPublic,
    UserUpdate,
    login_id_to_email,
)
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

router = APIRouter(tags=["login"])


@router.post("/login/access-token")
def login_access_token(
    session: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    # 아이디(@ 없음)도 받는다: 프론트 로그인 폼·Swagger Authorize가 이 경로를 쓴다
    login = form_data.username
    email = login if "@" in login else login_id_to_email(login)
    user = crud.authenticate(session=session, email=email, password=form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


def _issue_token(user: User) -> AuthResponse:
    token = security.create_access_token(
        user.id, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return AuthResponse(access_token=token, user=to_profile(user))


@router.get("/auth/check-username", response_model=UsernameCheck)
def check_username(
    session: SessionDep, username: Annotated[str, Query(pattern=USERNAME_PATTERN)]
) -> UsernameCheck:
    """
    아이디 중복 체크. 대소문자는 구분하지 않는다.
    """
    taken = session.exec(
        select(User.id).where(User.email == login_id_to_email(username))
    ).first()
    return UsernameCheck(username=username.lower(), available=taken is None)


@router.post("/auth/signup", response_model=AuthResponse)
def signup(session: SessionDep, body: AuthCredentials) -> AuthResponse:
    """
    아이디·비밀번호 가입. 가입 직후 로그인된 상태로 토큰을 돌려준다. 아이디가 이미 있으면 409.
    """
    username = body.username.lower()
    if session.exec(
        select(User.id).where(User.email == login_id_to_email(username))
    ).first():
        raise HTTPException(status_code=409, detail="Username already taken")
    user = User(
        nickname=username,
        email=login_id_to_email(username),
        hashed_password=security.get_password_hash(body.password),
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError:  # 동시에 같은 아이디로 가입한 경우
        session.rollback()
        raise HTTPException(status_code=409, detail="Username already taken")
    session.refresh(user)
    return _issue_token(user)


@router.post("/auth/login", response_model=AuthResponse)
def login(session: SessionDep, body: AuthCredentials) -> AuthResponse:
    """
    아이디·비밀번호 로그인.
    """
    user = session.exec(
        select(User).where(User.email == login_id_to_email(body.username))
    ).first()
    # 아이디가 없어도 해시 검증을 돌려 응답 시간 차이로 아이디 존재를 알아내지 못하게 한다.
    hashed = user.hashed_password if user else crud.DUMMY_HASH
    verified, new_hash = security.verify_password(body.password, hashed)
    if not user or not verified:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    if new_hash:
        user.hashed_password = new_hash
        session.add(user)
        session.commit()
        session.refresh(user)
    return _issue_token(user)


@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> Any:
    """
    Test access token
    """
    return current_user


@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SessionDep) -> Message:
    """
    Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    # Always return the same response to prevent email enumeration attacks
    # Only send email if user actually exists
    if user:
        password_reset_token = generate_password_reset_token(email=email)
        email_data = generate_reset_password_email(
            email_to=user.email, email=email, token=password_reset_token
        )
        send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return Message(
        message="If that email is registered, we sent a password recovery link"
    )


@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """
    Reset password
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")
    user = crud.get_user_by_email(session=session, email=email)
    if not user:
        # Don't reveal that the user doesn't exist - use same error as invalid token
        raise HTTPException(status_code=400, detail="Invalid token")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    user_in_update = UserUpdate(password=body.new_password)
    crud.update_user(
        session=session,
        db_user=user,
        user_in=user_in_update,
    )
    return Message(message="Password updated successfully")


@router.post(
    "/password-recovery-html-content/{email}",
    dependencies=[Depends(get_current_active_superuser)],
    response_class=HTMLResponse,
)
def recover_password_html_content(email: str, session: SessionDep) -> Any:
    """
    HTML Content for Password Recovery
    """
    user = crud.get_user_by_email(session=session, email=email)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="The user with this username does not exist in the system.",
        )
    password_reset_token = generate_password_reset_token(email=email)
    email_data = generate_reset_password_email(
        email_to=user.email, email=email, token=password_reset_token
    )

    return HTMLResponse(
        content=email_data.html_content, headers={"subject:": email_data.subject}
    )
