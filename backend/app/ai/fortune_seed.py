"""시드 문구 풀에서 (날짜, 팀)으로 운세를 고른다. 네트워크 호출이 없어 즉시 응답한다.

같은 날 같은 팀은 항상 같은 운세이고, 날짜가 바뀌면 달라진다.
같은 경기의 두 팀은 서로 다른 문구가 나온다.
"""

import hashlib
import json
import uuid
from datetime import date
from functools import lru_cache
from pathlib import Path

from app.ai.fortune import FortuneDraft

SEED_FILE = Path(__file__).parent / "fortune_seed.json"


@lru_cache
def _pool() -> dict[str, list[str] | int]:
    return json.loads(SEED_FILE.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _indexes(
    day: date, team_id: uuid.UUID, n_text: int, n_tip: int
) -> tuple[int, int, int]:
    digest = hashlib.sha256(f"{day.isoformat()}:{team_id}".encode()).digest()
    a, b, c = (int.from_bytes(digest[i : i + 4], "big") for i in (0, 4, 8))
    return a % n_text, b % n_tip, c


def pick_fortune(
    day: date, team_id: uuid.UUID, opponent_id: uuid.UUID, team_name: str
) -> FortuneDraft:
    pool = _pool()
    texts, tips = pool["fortune_texts"], pool["cheer_tips"]
    assert isinstance(texts, list) and isinstance(tips, list)
    lo, hi = pool["score_min"], pool["score_max"]
    assert isinstance(lo, int) and isinstance(hi, int)

    text_i, tip_i, raw_score = _indexes(day, team_id, len(texts), len(tips))
    opp_text_i, opp_tip_i, _ = _indexes(day, opponent_id, len(texts), len(tips))
    # 두 팀이 같은 칸이면 id가 큰 쪽만 한 칸 민다(양쪽이 같은 결론을 낸다).
    if str(team_id) > str(opponent_id):
        if text_i == opp_text_i:
            text_i = (text_i + 1) % len(texts)
        if tip_i == opp_tip_i:
            tip_i = (tip_i + 1) % len(tips)
    return FortuneDraft(
        fortune_text=texts[text_i].replace("{team}", team_name),
        cheer_tip=tips[tip_i],
        luck_score=lo + raw_score % (hi - lo + 1),
    )
