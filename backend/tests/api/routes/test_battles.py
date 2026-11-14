import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.api.routes.communities import get_or_create_community
from app.core.config import settings
from app.models import Battle, Match

API = settings.API_V1_STR


def _start(client: TestClient, db: Session, headers: dict[str, str]) -> dict:
    match = db.exec(select(Match)).first()
    assert match
    community = get_or_create_community(db, match.id)
    r = client.post(
        f"{API}/communities/{community.id}/battles",
        headers=headers,
        json={"duration_sec": 30},
    )
    assert r.status_code == 200
    return r.json()


def _finish(db: Session, battle_id: str) -> None:
    battle = db.get(Battle, uuid.UUID(battle_id))
    assert battle
    battle.ends_at = datetime.now(UTC) - timedelta(seconds=1)
    db.add(battle)
    db.commit()


def test_battle_flow_keeps_max_and_ranks(
    client: TestClient,
    db: Session,
    superuser_token_headers: dict[str, str],
    normal_user_token_headers: dict[str, str],
) -> None:
    battle = _start(client, db, superuser_token_headers)
    # 진행 중에 다시 시작하면 같은 대결에 합류
    again = _start(client, db, normal_user_token_headers)
    assert again["id"] == battle["id"]
    bid = battle["id"]

    for peak in (95.0, 88.0):  # 낮은 값이 와도 최고값 유지
        client.post(
            f"{API}/battles/{bid}/records",
            headers=superuser_token_headers,
            json={"peak_db": peak},
        )
    r = client.post(
        f"{API}/battles/{bid}/records",
        headers=normal_user_token_headers,
        json={"peak_db": 101.5},
    )
    state = r.json()
    assert state["status"] == "ONGOING"
    assert [e["peak_db"] for e in state["leaderboard"]] == [101.5, 95.0]
    assert state["me"] == {"rank": 1, "peak_db": 101.5}

    _finish(db, bid)
    r = client.get(f"{API}/battles/{bid}/result", headers=superuser_token_headers)
    assert r.status_code == 200
    result = r.json()
    assert result["me"] == {"rank": 2, "peak_db": 95.0}
    assert result["my_top_percent"] == 100
    assert len(result["top3"]) == 2


def test_submit_after_end_is_rejected(
    client: TestClient, db: Session, superuser_token_headers: dict[str, str]
) -> None:
    battle = _start(client, db, superuser_token_headers)
    _finish(db, battle["id"])
    r = client.post(
        f"{API}/battles/{battle['id']}/records",
        headers=superuser_token_headers,
        json={"peak_db": 120},
    )
    assert r.status_code == 409
    r = client.get(f"{API}/battles/{battle['id']}", headers=superuser_token_headers)
    assert r.json()["status"] == "FINISHED"
