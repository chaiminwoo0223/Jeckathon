"""선수 생년월일 기반 운세. 규칙의 정본은 docs/cheer101-spec.md §4.7.

경기일(KST)과 선수 생년월일만으로 결정되므로 같은 날은 항상 같은 결과다.
문구는 fortune_grades.json 시드에서 고른다(네트워크·DB 저장 없음).
"""

import hashlib
import json
import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.ai.fortune import FortuneDraft
from app.ai.fortune_seed import pick_fortune
from app.models import FortuneGrade, FortunePlayer, Player

GRADES_FILE = Path(__file__).parent / "fortune_grades.json"

LUCKY_COUNT = 3  # 기운 좋은 선수 수
MIN_CANDIDATES = LUCKY_COUNT + 1  # 이보다 적으면 팀 시드로 폴백
MAX_BACK_NUMBER = 99  # 3자리(육성) 등번호는 후보에서 뺀다

# (최소 점수, 등급) — 위에서부터 처음 맞는 등급
GRADE_THRESHOLDS: tuple[tuple[int, FortuneGrade], ...] = (
    (88, FortuneGrade.BEST),
    (68, FortuneGrade.GOOD),
    (43, FortuneGrade.SMALL_GOOD),
    (23, FortuneGrade.SMALL_BAD),
    (8, FortuneGrade.BAD),
    (0, FortuneGrade.WORST),
)
BAD_GRADES = frozenset({FortuneGrade.SMALL_BAD, FortuneGrade.BAD, FortuneGrade.WORST})

# 0~99 균등 분포의 평균·표준편차 (팀 점수 퍼센타일 변환에 쓴다)
_SCORE_MEAN = 49.5
_SCORE_SD = math.sqrt((100**2 - 1) / 12)


@dataclass(frozen=True)
class Side:
    """운세를 만드는 한 팀(후보는 DB의 Player 그대로 넣고, 거르는 건 여기서 한다)."""

    team_id: uuid.UUID
    name: str
    players: Sequence[Player]


@dataclass(frozen=True)
class TeamFortune:
    draft: FortuneDraft
    grade: FortuneGrade
    lucky_players: list[FortunePlayer]
    caution_player: FortunePlayer | None


@lru_cache
def _pool() -> dict[str, Any]:
    return json.loads(GRADES_FILE.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _digest_ints(key: str) -> tuple[int, int]:
    digest = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(digest[:4], "big"), int.from_bytes(digest[4:8], "big")


def is_candidate(player: Player) -> bool:
    """등번호 0~99인 선수만 후보. 1군 구분 데이터가 없어 육성·미등록을 거르는 근사치."""
    number = player.back_number
    return number is not None and number.isdigit() and int(number) <= MAX_BACK_NUMBER


def grade_of(score: int) -> FortuneGrade:
    for minimum, grade in GRADE_THRESHOLDS:
        if score >= minimum:
            return grade
    return FortuneGrade.WORST


def player_score(birth_date: date, day: date) -> int:
    """선수 점수 0~99. 같은 생일이면 같은 점수."""
    return _digest_ints(f"{birth_date.isoformat()}:{day.isoformat()}")[0] % 100


def team_score(scores: Sequence[int]) -> int:
    """후보 점수 평균을 퍼센타일(0~100)로 바꿔 6단계가 고르게 나오게 한다."""
    n = len(scores)
    z = (sum(scores) / n - _SCORE_MEAN) / (_SCORE_SD / math.sqrt(n))
    return round(100 * 0.5 * (1 + math.erf(z / math.sqrt(2))))


def _ranked(players: Sequence[Player], day: date) -> list[tuple[int, Player]]:
    """후보를 점수 내림차순으로. 동점은 kbo_id 오름차순."""
    scored = [(player_score(p.birth_date, day), p) for p in players if is_candidate(p)]
    return sorted(scored, key=lambda sp: (-sp[0], sp[1].kbo_id))


def _to_public(player: Player, score: int, day: date) -> FortunePlayer:
    grade = grade_of(score)
    lines = _pool()["team"][grade.value]["player_one_liners"]
    index = _digest_ints(f"{day.isoformat()}:{player.kbo_id}:{grade.value}")[0]
    return FortunePlayer(
        kbo_id=player.kbo_id,
        name=player.name,
        position=player.position,
        back_number=player.back_number,
        birth_year=player.birth_date.year,
        grade=grade,
        luck_score=score,
        one_liner=lines[index % len(lines)].replace("{player}", player.name),
    )


def _text_indexes(
    day: date, team_id: uuid.UUID, grade: FortuneGrade
) -> tuple[int, int]:
    pool = _pool()["team"][grade.value]
    a, b = _digest_ints(f"{day.isoformat()}:{team_id}:{grade.value}")
    return a % len(pool["fortune_texts"]), b % len(pool["cheer_tips"])


def build_fortune(day: date, team: Side, opponent: Side) -> TeamFortune:
    """응원팀(team)의 운세. 후보가 너무 적으면 기존 팀 시드로 폴백한다."""
    mine = _ranked(team.players, day)
    if len(mine) < MIN_CANDIDATES:
        draft = pick_fortune(day, team.team_id, opponent.team_id, team.name)
        return TeamFortune(draft, grade_of(draft.luck_score), [], None)

    score = team_score([s for s, _ in mine])
    grade = grade_of(score)
    pool = _pool()["team"][grade.value]
    text_i, tip_i = _text_indexes(day, team.team_id, grade)

    # 상대 팀도 같은 등급이고 같은 칸이면 id 큰 쪽만 한 칸 민다(양쪽이 같은 결론을 낸다)
    theirs = _ranked(opponent.players, day)
    if len(theirs) >= MIN_CANDIDATES and str(team.team_id) > str(opponent.team_id):
        opp_grade = grade_of(team_score([s for s, _ in theirs]))
        if opp_grade == grade:
            opp_text_i, opp_tip_i = _text_indexes(day, opponent.team_id, grade)
            if text_i == opp_text_i:
                text_i = (text_i + 1) % len(pool["fortune_texts"])
            if tip_i == opp_tip_i:
                tip_i = (tip_i + 1) % len(pool["cheer_tips"])

    lucky = [_to_public(p, s, day) for s, p in mine[:LUCKY_COUNT]]
    worst_score, worst = mine[-1]
    caution = (
        _to_public(worst, worst_score, day)
        if grade_of(worst_score) in BAD_GRADES
        else None
    )
    draft = FortuneDraft(
        fortune_text=pool["fortune_texts"][text_i].replace("{team}", team.name),
        cheer_tip=pool["cheer_tips"][tip_i],
        luck_score=score,
    )
    return TeamFortune(draft, grade, lucky, caution)
