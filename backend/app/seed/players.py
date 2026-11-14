"""KBO 선수 명단 시드(운세 입력). kbo_people_2026.json에서 선수만 넣는다.

kbo_id로 upsert하므로 파일을 새 명단으로 바꾸고 다시 돌려도 안전하다.
"""

import json
from datetime import date
from pathlib import Path

from sqlmodel import Session, select

from app.models import Player, Team

PEOPLE_FILE = Path(__file__).parent / "kbo_people_2026.json"

# KBO 팀 코드 → Team.name
TEAM_BY_KBO_CODE = {
    "LG": "LG",
    "HH": "한화",
    "SK": "SSG",
    "SS": "삼성",
    "NC": "NC",
    "KT": "KT",
    "LT": "롯데",
    "HT": "KIA",
    "OB": "두산",
    "WO": "키움",
}


def seed_players(session: Session) -> None:
    if not PEOPLE_FILE.exists():
        return
    teams = {t.name: t for t in session.exec(select(Team)).all()}
    existing = {p.kbo_id: p for p in session.exec(select(Player)).all()}
    for entry in json.loads(PEOPLE_FILE.read_text(encoding="utf-8"))["teams"]:
        team = teams.get(TEAM_BY_KBO_CODE.get(entry["code"], ""))
        if team is None:
            continue
        for raw in entry["people"]:
            if raw["role"] != "선수" or not raw.get("birth_date"):
                continue
            position = raw.get("position") or ""
            birth_date = date.fromisoformat(raw["birth_date"])
            player = existing.get(raw["kbo_id"])
            if player is None:
                player = Player(
                    kbo_id=raw["kbo_id"],
                    team_id=team.id,
                    name=raw["name"],
                    position=position,
                    back_number=raw.get("back_number"),
                    birth_date=birth_date,
                )
            else:
                player.team_id = team.id
                player.name = raw["name"]
                player.position = position
                player.back_number = raw.get("back_number")
                player.birth_date = birth_date
            session.add(player)
    session.commit()
