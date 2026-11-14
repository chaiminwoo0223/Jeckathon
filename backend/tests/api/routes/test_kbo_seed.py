from fastapi.testclient import TestClient
from sqlmodel import Session, func, select

from app.core.config import settings
from app.models import Match
from app.seed.kbo import seed_kbo


def test_teams_have_short_name_and_color(client: TestClient) -> None:
    teams = client.get(f"{settings.API_V1_STR}/teams/").json()["data"]
    kbo = {t["name"]: t for t in teams if t["league"] == "KBO리그"}
    assert len(kbo) == 10
    assert kbo["LG"]["short_name"] == "LG"
    assert all(t["short_name"] and t["color"].startswith("#") for t in kbo.values())


def test_real_season_game_is_seeded(client: TestClient) -> None:
    body = client.get(
        f"{settings.API_V1_STR}/matches/", params={"month": "2026-11"}
    ).json()
    games = [m for d in body["days"] if d["date"] == "2026-11-08" for m in d["matches"]]
    ks5 = next(m for m in games if m["round_label"] == "KS 5차전")
    assert ks5["home_team"]["name"] == "삼성"
    assert ks5["away_team"]["name"] == "KT"
    assert (ks5["home_score"], ks5["away_score"]) == (12, 1)
    assert ks5["status"] == "FINISHED"
    assert ks5["venue"] == "대구"


def test_seed_is_idempotent(db: Session) -> None:
    before = db.exec(select(func.count()).select_from(Match)).one()
    seed_kbo(db)
    after = db.exec(select(func.count()).select_from(Match)).one()
    assert after == before
