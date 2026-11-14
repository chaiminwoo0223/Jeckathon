import uuid

from fastapi.testclient import TestClient

from app.core.config import settings

API = settings.API_V1_STR


def _name() -> str:
    return f"u{uuid.uuid4().hex[:12]}"


def test_check_username_available_then_taken(client: TestClient) -> None:
    name = _name()
    r = client.get(f"{API}/auth/check-username", params={"username": name})
    assert r.status_code == 200
    assert r.json() == {"username": name, "available": True}

    client.post(f"{API}/auth/signup", json={"username": name, "password": "pw1234"})
    r = client.get(f"{API}/auth/check-username", params={"username": name})
    assert r.json()["available"] is False
    # 대소문자는 구분하지 않는다
    r = client.get(f"{API}/auth/check-username", params={"username": name.upper()})
    assert r.json() == {"username": name, "available": False}


def test_check_username_rejects_bad_format(client: TestClient) -> None:
    for bad in ("abc", "a" * 21, "한글아이디", "has space", "a-b-c-d"):
        r = client.get(f"{API}/auth/check-username", params={"username": bad})
        assert r.status_code == 422, bad


def test_signup_returns_token_and_profile(client: TestClient) -> None:
    name = _name()
    r = client.post(f"{API}/auth/signup", json={"username": name, "password": "pw1234"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["nickname"] == name  # 닉네임 기본값은 아이디
    assert "username" not in body["user"]
    assert "email" not in body["user"]
    assert body["user"]["level"] == 1
    assert "password" not in str(body)
    me = client.get(
        f"{API}/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["id"] == body["user"]["id"]


def test_signup_duplicate_is_409(client: TestClient) -> None:
    name = _name()
    body = {"username": name, "password": "pw1234"}
    assert client.post(f"{API}/auth/signup", json=body).status_code == 200
    assert client.post(f"{API}/auth/signup", json=body).status_code == 409
    upper = {"username": name.upper(), "password": "other1234"}
    assert client.post(f"{API}/auth/signup", json=upper).status_code == 409


def test_signup_validation(client: TestClient) -> None:
    for payload in (
        {"username": "ab", "password": "pw1234"},
        {"username": _name(), "password": "abc"},
        {"username": "bad name", "password": "pw1234"},
        {"username": _name()},
    ):
        assert client.post(f"{API}/auth/signup", json=payload).status_code == 422


def test_login_success_and_case_insensitive(client: TestClient) -> None:
    name = _name()
    signup = client.post(
        f"{API}/auth/signup", json={"username": name, "password": "pw1234"}
    ).json()
    r = client.post(
        f"{API}/auth/login", json={"username": name.upper(), "password": "pw1234"}
    )
    assert r.status_code == 200
    assert r.json()["user"]["id"] == signup["user"]["id"]
    assert r.json()["access_token"]


def test_login_failures_look_the_same(client: TestClient) -> None:
    name = _name()
    client.post(f"{API}/auth/signup", json={"username": name, "password": "pw1234"})
    wrong_pw = client.post(
        f"{API}/auth/login", json={"username": name, "password": "wrong-pw"}
    )
    no_user = client.post(
        f"{API}/auth/login", json={"username": _name(), "password": "pw1234"}
    )
    assert wrong_pw.status_code == no_user.status_code == 400
    assert wrong_pw.json() == no_user.json()  # 아이디 존재 여부를 알 수 없다


def test_username_login_does_not_reach_template_accounts(client: TestClient) -> None:
    """관리자 계정은 이메일(템플릿 로그인)로만 들어간다. 아이디 로그인에는 username이 없다."""
    r = client.post(
        f"{API}/auth/login",
        json={
            "username": settings.FIRST_SUPERUSER,  # 이메일은 아이디 형식이 아니다
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        },
    )
    assert r.status_code == 422
    local = settings.FIRST_SUPERUSER.split("@")[0]
    r = client.post(
        f"{API}/auth/login",
        json={"username": local, "password": settings.FIRST_SUPERUSER_PASSWORD},
    )
    assert r.status_code == 400
