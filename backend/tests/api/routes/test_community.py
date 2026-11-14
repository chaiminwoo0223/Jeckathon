import uuid
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlmodel import Session, col, delete, func, select

from app.core.config import settings
from app.models import (
    CheerRecord,
    CheerResult,
    Community,
    CommunityMember,
    Match,
    MatchStatus,
    Team,
)
from app.services import community as community_service

API = settings.API_V1_STR
KST = timezone(timedelta(hours=9))

_created_matches: list[uuid.UUID] = []


@pytest.fixture(scope="module", autouse=True)
def _cleanup(db: Session) -> Generator[None]:
    """이 파일이 만든 경기와 커뮤니티만 지운다(멤버·응원 기록은 FK cascade)."""
    yield
    if _created_matches:
        db.execute(
            delete(Community).where(col(Community.match_id).in_(_created_matches))
        )
        db.execute(delete(Match).where(col(Match.id).in_(_created_matches)))
        db.commit()


class Fan:
    def __init__(self, client: TestClient) -> None:
        name = f"u{uuid.uuid4().hex[:12]}"
        r = client.post(
            f"{API}/auth/signup", json={"username": name, "password": "pw1234"}
        )
        self.client = client
        self.name = name
        self.headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        self.id = uuid.UUID(r.json()["user"]["id"])

    def cheer(self, match: Match) -> None:
        r = self.client.post(
            f"{API}/matches/{match.id}/cheer",
            headers=self.headers,
            json={"cheered_team_id": str(match.home_team_id)},
        )
        assert r.status_code == 200, r.text

    def community_of(self, match: Match) -> dict:
        r = self.client.get(f"{API}/matches/{match.id}/community", headers=self.headers)
        assert r.status_code == 200, r.text
        return r.json()

    def join(self, community_id: str) -> Response:
        return self.client.post(
            f"{API}/communities/{community_id}/join", headers=self.headers
        )

    def mine(self) -> dict:
        r = self.client.get(f"{API}/communities/mine", headers=self.headers)
        assert r.status_code == 200, r.text
        return r.json()


def _match(
    db: Session,
    kickoff: datetime,
    status: MatchStatus = MatchStatus.SCHEDULED,
) -> Match:
    t1, t2 = db.exec(select(Team).limit(2)).all()
    match = Match(
        home_team_id=t1.id,
        away_team_id=t2.id,
        league="KBO리그",
        kickoff_at=kickoff,
        status=status,
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    _created_matches.append(match.id)
    return match


def _in(minutes: int) -> datetime:
    return datetime.now(UTC) + timedelta(minutes=minutes)


# --- 입장 규칙 (순수 함수) ---


def test_enter_window_boundaries() -> None:
    kickoff = datetime(2026, 11, 14, 18, 0, tzinfo=UTC)
    m = Match(
        home_team_id=uuid.uuid4(),
        away_team_id=uuid.uuid4(),
        league="KBO",
        kickoff_at=kickoff,
        status=MatchStatus.SCHEDULED,
    )
    opens = kickoff - timedelta(hours=1)
    assert community_service.enter_window(m, opens - timedelta(seconds=1)) == (
        opens,
        False,
    )
    assert community_service.enter_window(m, opens) == (opens, True)  # 정확히 1시간 전
    assert community_service.enter_window(m, kickoff + timedelta(hours=2))[1] is True
    m.status = MatchStatus.LIVE
    assert community_service.enter_window(m, kickoff)[1] is True
    m.status = MatchStatus.FINISHED
    assert community_service.enter_window(m, kickoff + timedelta(hours=1))[1] is False


# --- 인증 ---


def test_endpoints_require_auth(client: TestClient) -> None:
    some = uuid.uuid4()
    for method, path in [
        ("get", "/communities/mine"),
        ("get", f"/matches/{some}/community"),
        ("post", f"/communities/{some}/join"),
        ("post", f"/communities/{some}/leave"),
        ("get", f"/communities/{some}/members"),
    ]:
        assert client.request(method, f"{API}{path}").status_code == 401, path


# --- GET /communities/mine ---


def test_mine_is_empty_without_cheers(client: TestClient) -> None:
    fan = Fan(client)
    body = fan.mine()
    assert (body["count"], body["days"]) == (0, [])
    assert body["server_now"]


def test_mine_groups_by_kst_date_in_order(client: TestClient, db: Session) -> None:
    fan, other = Fan(client), Fan(client)
    day = datetime.now(KST).date() + timedelta(days=60)

    def at(d: object, h: int, m: int) -> datetime:
        return datetime(d.year, d.month, d.day, h, m, tzinfo=KST)

    late = _match(db, at(day, 23, 30))
    early = _match(db, at(day, 0, 30))  # UTC로는 전날 15:30이다
    next_day = _match(db, at(day + timedelta(days=1), 10, 0))
    finished = _match(db, at(day, 12, 0), MatchStatus.FINISHED)
    unapplied = _match(db, at(day, 18, 0))
    for m in (late, early, next_day):
        fan.cheer(m)
    db.add(  # 종료된 경기는 응원 기록이 있어도 목록에서 빠진다
        CheerRecord(
            user_id=fan.id,
            match_id=finished.id,
            cheered_team_id=finished.home_team_id,
            result=CheerResult.WIN,
        )
    )
    db.commit()
    other.cheer(unapplied)  # 남의 신청은 내 목록에 없다

    body = fan.mine()
    assert body["count"] == 3
    assert [d["date"] for d in body["days"]] == [
        day.isoformat(),
        (day + timedelta(days=1)).isoformat(),
    ]
    first_day = body["days"][0]["items"]
    assert [i["match"]["id"] for i in first_day] == [str(early.id), str(late.id)]
    item = first_day[0]
    assert item["match"]["home_team"]["name"]
    assert item["cheered_team_id"] == str(early.home_team_id)
    assert item["community"]["member_count"] == 0
    assert item["community"]["joined"] is False
    assert item["can_enter"] is False  # 60일 뒤 경기


def test_mine_reports_enter_state(client: TestClient, db: Session) -> None:
    fan = Fan(client)
    soon = _match(db, _in(30))  # 30분 뒤: 이미 입장 가능
    later = _match(db, _in(120))  # 2시간 뒤: 아직
    fan.cheer(soon)
    fan.cheer(later)
    items = {i["match"]["id"]: i for d in fan.mine()["days"] for i in d["items"]}
    assert items[str(soon.id)]["can_enter"] is True
    assert items[str(later.id)]["can_enter"] is False
    opens = datetime.fromisoformat(items[str(later.id)]["enter_opens_at"])
    assert opens == later.kickoff_at - timedelta(hours=1)

    cid = items[str(soon.id)]["community"]["id"]
    assert fan.join(cid).status_code == 200
    joined = {i["match"]["id"]: i for d in fan.mine()["days"] for i in d["items"]}
    assert joined[str(soon.id)]["community"]["joined"] is True
    assert joined[str(soon.id)]["community"]["member_count"] == 1


# --- GET /matches/{id}/community ---


def test_match_community_info(client: TestClient, db: Session) -> None:
    fan = Fan(client)
    match = _match(db, _in(30))
    info = fan.community_of(match)
    assert (info["match_id"], info["member_count"], info["joined"]) == (
        str(match.id),
        0,
        False,
    )
    assert info["can_enter"] is True
    assert datetime.fromisoformat(
        info["enter_opens_at"]
    ) == match.kickoff_at - timedelta(hours=1)
    assert fan.community_of(match)["id"] == info["id"]  # 다시 불러도 같은 커뮤니티
    r = client.get(f"{API}/matches/{uuid.uuid4()}/community", headers=fan.headers)
    assert r.status_code == 404


# --- join / leave ---


def test_join_requires_cheer_and_open_window(client: TestClient, db: Session) -> None:
    fan = Fan(client)
    open_match = _match(db, _in(30))
    cid = fan.community_of(open_match)["id"]

    r = fan.join(cid)  # 열려 있어도 신청하지 않았으면 거절
    assert r.status_code == 403
    assert r.json()["detail"] == {"code": "NOT_CHEERED"}

    closed = _match(db, _in(61))  # 1시간 1분 뒤: 아직 닫혀 있다
    fan.cheer(closed)
    r = fan.join(fan.community_of(closed)["id"])
    assert r.status_code == 403
    detail = r.json()["detail"]
    assert detail["code"] == "NOT_OPEN_YET"
    assert datetime.fromisoformat(
        detail["enter_opens_at"]
    ) == closed.kickoff_at - timedelta(hours=1)
    assert fan.community_of(closed)["member_count"] == 0  # 거절됐으니 멤버가 아니다

    just_open = _match(db, _in(59))  # 59분 뒤: 열렸다
    fan.cheer(just_open)
    assert fan.join(fan.community_of(just_open)["id"]).status_code == 200


def test_join_rejects_finished_match(client: TestClient, db: Session) -> None:
    fan = Fan(client)
    match = _match(db, _in(-300), MatchStatus.FINISHED)
    db.add(
        CheerRecord(
            user_id=fan.id,
            match_id=match.id,
            cheered_team_id=match.home_team_id,
            result=CheerResult.LOSE,
        )
    )
    db.commit()
    r = fan.join(fan.community_of(match)["id"])
    assert r.status_code == 409
    assert r.json()["detail"] == {"code": "MATCH_FINISHED"}


def test_join_not_found(client: TestClient) -> None:
    fan = Fan(client)
    assert fan.join(str(uuid.uuid4())).status_code == 404


def test_join_is_idempotent_then_leave(client: TestClient, db: Session) -> None:
    a, b = Fan(client), Fan(client)
    match = _match(db, _in(30))
    a.cheer(match)
    b.cheer(match)
    cid = a.community_of(match)["id"]

    assert a.join(cid).json()["member_count"] == 1
    again = a.join(cid).json()
    assert (again["member_count"], again["joined"]) == (1, True)
    assert b.join(cid).json()["member_count"] == 2

    r = client.post(f"{API}/communities/{cid}/leave", headers=a.headers)
    assert r.status_code == 200
    assert (r.json()["member_count"], r.json()["joined"]) == (1, False)
    # 멤버가 아니어도 나가기는 성공한다
    r = client.post(f"{API}/communities/{cid}/leave", headers=a.headers)
    assert (r.status_code, r.json()["member_count"]) == (200, 1)
    assert b.community_of(match)["joined"] is True  # 다른 사람은 그대로
    r = client.post(f"{API}/communities/{uuid.uuid4()}/leave", headers=a.headers)
    assert r.status_code == 404


# --- members ---


def test_members_list_with_fairy_type(client: TestClient, db: Session) -> None:
    winner, loser, rookie = Fan(client), Fan(client), Fan(client)
    match = _match(db, _in(30))
    for f in (winner, loser, rookie):
        f.cheer(match)
    for f, result in ((winner, CheerResult.WIN), (loser, CheerResult.LOSE)):
        past = _match(db, _in(-1000), MatchStatus.FINISHED)
        db.add(
            CheerRecord(
                user_id=f.id,
                match_id=past.id,
                cheered_team_id=past.home_team_id,
                result=result,
            )
        )
    db.commit()
    client.patch(
        f"{API}/me/profile", headers=winner.headers, json={"nickname": "뚜비응원단"}
    )
    cid = winner.community_of(match)["id"]
    for f in (winner, loser, rookie):  # 입장 순서를 보장하려고 순서대로
        assert f.join(cid).status_code == 200

    r = client.get(f"{API}/communities/{cid}/members", headers=rookie.headers)
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 3
    assert [m["user_id"] for m in body["data"]] == [
        str(f.id) for f in (winner, loser, rookie)
    ]
    by_id = {m["user_id"]: m for m in body["data"]}
    assert by_id[str(winner.id)]["fairy_type"] == "VICTORY"
    assert by_id[str(winner.id)]["fairy_label"] == "승리요정 뚜비응원단"
    assert by_id[str(loser.id)]["fairy_type"] == "DEFEAT"
    assert by_id[str(rookie.id)]["fairy_type"] == "NEUTRAL"
    assert {"nickname", "profile_image_url", "level", "joined_at"} <= set(
        body["data"][0]
    )

    r = client.get(f"{API}/communities/{uuid.uuid4()}/members", headers=rookie.headers)
    assert r.status_code == 404


def test_members_empty(client: TestClient, db: Session) -> None:
    fan = Fan(client)
    match = _match(db, _in(30))
    cid = fan.community_of(match)["id"]
    r = client.get(f"{API}/communities/{cid}/members", headers=fan.headers)
    assert r.json() == {"data": [], "count": 0}


# --- 동시성 ---


def test_concurrent_requests_create_one_community_and_one_member(
    client: TestClient, db: Session
) -> None:
    fan = Fan(client)
    match = _match(db, _in(30))
    fan.cheer(match)

    def info(_: int) -> int:
        return client.get(
            f"{API}/matches/{match.id}/community", headers=fan.headers
        ).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert set(pool.map(info, range(8))) == {200}
    count = db.exec(
        select(func.count())
        .select_from(Community)
        .where(Community.match_id == match.id)
    ).one()
    assert count == 1  # 동시에 만들어도 경기당 하나

    cid = str(db.exec(select(Community.id).where(Community.match_id == match.id)).one())

    def join(_: int) -> int:
        return client.post(
            f"{API}/communities/{cid}/join", headers=fan.headers
        ).status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert set(pool.map(join, range(8))) == {200}
    db.expire_all()
    members = db.exec(
        select(func.count())
        .select_from(CommunityMember)
        .where(CommunityMember.community_id == uuid.UUID(cid))
    ).one()
    assert members == 1  # 같은 유저가 동시에 눌러도 멤버는 한 명
