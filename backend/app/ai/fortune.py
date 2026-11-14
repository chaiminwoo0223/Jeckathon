"""AI 운세 생성(보관). 지금 라우트는 시드 풀(fortune_seed.py)만 쓰고, AI 연동 때 다시 연결한다."""

import json
import logging
import re
import uuid
from dataclasses import dataclass

import httpx
from sqlmodel import Session, col, select

from app.core.config import settings
from app.models import Match, MatchStatus

logger = logging.getLogger(__name__)

AI_URL = "https://api.anthropic.com/v1/messages"
AI_MODEL = "claude-haiku-5-5"
AI_TIMEOUT_SEC = 10.0

TEXT_MAX = 500
TIP_MAX = 300

SYSTEM_PROMPT = (
    "너는 스포츠 팬을 위한 '쓸모없지만 그럴듯한' 운세 작가다. "
    "응원하는 팀의 오늘 경기 운세를 재치 있고 가볍게, 한국어로 쓴다. "
    "실제 선수 이름이나 확인되지 않은 사실, 도박·승부 예측 단정은 쓰지 않는다. "
    '반드시 JSON 한 개만 출력한다: {"fortune_text": "1~2문장", "cheer_tip": "한 문장 응원 팁", '
    '"luck_score": 0~100 정수}'
)


@dataclass(frozen=True)
class FortuneDraft:
    fortune_text: str
    cheer_tip: str
    luck_score: int


def build_prompt(team: str, opponent: str, recent_form: str | None) -> str:
    lines = [f"응원팀: {team}", f"상대팀: {opponent}"]
    if recent_form:
        lines.append(f"최근 전적(최신순, W=승 L=패 D=무): {recent_form}")
    lines.append("오늘 경기 운세를 만들어줘.")
    return "\n".join(lines)


def parse_draft(raw: str) -> FortuneDraft | None:
    """모델 응답에서 JSON을 꺼내 검증한다. 형식이 어긋나면 None."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match is None:
        return None
    try:
        data = json.loads(match.group(0))
        text = str(data["fortune_text"]).strip()
        tip = str(data["cheer_tip"]).strip()
        score = int(data["luck_score"])
    except ValueError, KeyError, TypeError:
        return None
    if not text or not tip:
        return None
    return FortuneDraft(text[:TEXT_MAX], tip[:TIP_MAX], max(0, min(100, score)))


def generate_fortune(
    team: str, opponent: str, recent_form: str | None
) -> FortuneDraft | None:
    """AI로 운세를 만든다. 키가 없거나 실패하면 None(호출한 쪽이 고정 문구로 대체)."""
    if not settings.AI_API_KEY:
        return None
    try:
        response = httpx.post(
            AI_URL,
            headers={
                "x-api-key": settings.AI_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": AI_MODEL,
                "max_tokens": 400,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {
                        "role": "user",
                        "content": build_prompt(team, opponent, recent_form),
                    }
                ],
            },
            timeout=AI_TIMEOUT_SEC,
        )
        response.raise_for_status()
        content = response.json()["content"]
        raw = "".join(b.get("text", "") for b in content if b.get("type") == "text")
    except httpx.HTTPError, ValueError, KeyError, TypeError:
        logger.warning("fortune AI call failed", exc_info=True)
        return None
    draft = parse_draft(raw)
    if draft is None:
        logger.warning("fortune AI response not parseable: %r", raw[:200])
    return draft


RECENT_FORM_COUNT = 5


def recent_form(session: Session, match: Match, team_id: uuid.UUID) -> str | None:
    """이 경기 이전 종료 경기 최근 5개를 'WWLDW'(최신순)로. 없으면 None. AI 프롬프트용."""
    rows = session.exec(
        select(Match)
        .where(
            col(Match.status) == MatchStatus.FINISHED,
            col(Match.kickoff_at) < match.kickoff_at,
            (col(Match.home_team_id) == team_id) | (col(Match.away_team_id) == team_id),
        )
        .order_by(col(Match.kickoff_at).desc())
        .limit(RECENT_FORM_COUNT)
    ).all()
    form = ""
    for m in rows:
        if m.home_score is None or m.away_score is None:
            continue
        mine, theirs = (
            (m.home_score, m.away_score)
            if m.home_team_id == team_id
            else (m.away_score, m.home_score)
        )
        form += "W" if mine > theirs else "L" if mine < theirs else "D"
    return form or None
