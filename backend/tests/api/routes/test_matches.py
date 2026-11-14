import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.config import settings

KST = timezone(timedelta(hours=9))


def test_read_teams(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/teams/")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 6
    assert {"LG", "두산"} <= {t["name"] for t in body["data"]}


def test_read_matches_today(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/matches/today")
    assert r.status_code == 200
    body = r.json()
    assert body["date"] == datetime.now(KST).date().isoformat()
    assert body["count"] == len(body["data"])
    for m in body["data"]:
        assert m["home_team"]["name"] and m["away_team"]["name"]


def test_read_matches_by_month_groups_by_date(client: TestClient) -> None:
    month = datetime.now(KST).strftime("%Y-%m")
    r = client.get(f"{settings.API_V1_STR}/matches/", params={"month": month})
    assert r.status_code == 200
    body = r.json()
    assert body["month"] == month
    dates = [d["date"] for d in body["days"]]
    assert dates == sorted(dates)
    assert all(d.startswith(month) for d in dates)
    assert body["count"] == sum(len(d["matches"]) for d in body["days"])


def test_read_matches_by_month_invalid(client: TestClient) -> None:
    for bad in ("2026-13", "2026-1", "abc"):
        r = client.get(f"{settings.API_V1_STR}/matches/", params={"month": bad})
        assert r.status_code == 422
    assert client.get(f"{settings.API_V1_STR}/matches/").status_code == 422


def test_read_match(client: TestClient) -> None:
    today = client.get(f"{settings.API_V1_STR}/matches/today").json()["data"]
    assert today, "시드에 오늘 경기가 있어야 한다"
    r = client.get(f"{settings.API_V1_STR}/matches/{today[0]['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == today[0]["id"]
    assert r.json()["status"] == "SCHEDULED"


def test_read_match_not_found(client: TestClient) -> None:
    r = client.get(f"{settings.API_V1_STR}/matches/{uuid.uuid4()}")
    assert r.status_code == 404
