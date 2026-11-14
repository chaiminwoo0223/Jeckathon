"""승률·요정 판정 (명세 §3.1, §3.2). CheerRecord 집계는 정산 단계에서 이 함수들을 쓴다."""

from app.models import FairyType, StatsPublic

VICTORY_WIN_RATE = 0.6  # 승률 이 값 이상이면 승리요정
DEFEAT_LOSE_RATE = 0.3  # 패배율 이 값 이상이면 패배요정 (승리요정이 우선)

_FAIRY_LABEL = {
    FairyType.VICTORY: "승리요정",
    FairyType.DEFEAT: "패배요정",
    FairyType.NEUTRAL: "중립요정",
}


def rates(win: int, lose: int) -> tuple[float, float]:
    """(승률, 패배율). 분모는 무승부를 뺀 승+패이고, 0이면 둘 다 0."""
    decided = win + lose
    if decided == 0:
        return 0.0, 0.0
    return win / decided, lose / decided


def fairy_type(win: int, lose: int) -> FairyType:
    win_rate, lose_rate = rates(win, lose)
    if win_rate >= VICTORY_WIN_RATE:
        return FairyType.VICTORY
    if lose_rate >= DEFEAT_LOSE_RATE:
        return FairyType.DEFEAT
    return FairyType.NEUTRAL


def fairy_label(fairy: FairyType, nickname: str) -> str:
    return f"{_FAIRY_LABEL[fairy]} {nickname}"


def build_stats(win: int, draw: int, lose: int) -> StatsPublic:
    win_rate, lose_rate = rates(win, lose)
    return StatsPublic(
        total=win + draw + lose,
        win=win,
        draw=draw,
        lose=lose,
        win_rate=round(win_rate, 2),
        lose_rate=round(lose_rate, 2),
    )
