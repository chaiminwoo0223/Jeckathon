import uuid
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.ai.fortune_players import Side, build_fortune
from app.api.deps import SessionDep
from app.api.routes.matches import KST
from app.models import FortunePublic, Match, Player, Team

router = APIRouter(prefix="/matches", tags=["fortune"])


@router.get("/{id}/fortune", response_model=FortunePublic)
def read_fortune(
    session: SessionDep,
    id: uuid.UUID,
    team_id: Annotated[uuid.UUID, Query()],
) -> Any:
    """
    경기 당일 응원팀 운세. 두 팀 선수의 생년월일로 등급·선수 하이라이트를 계산하고
    문구는 시드 풀에서 고른다. 같은 날 같은 팀은 항상 같은 운세이고 DB에 저장하지 않는다
    (규칙은 명세 §4.7, AI 연동은 후속).
    """
    match = session.get(Match, id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    if team_id not in (match.home_team_id, match.away_team_id):
        raise HTTPException(
            status_code=400, detail="Team must be the home or away team"
        )
    opponent_id = (
        match.away_team_id if team_id == match.home_team_id else match.home_team_id
    )
    team = session.get(Team, team_id)
    opponent = session.get(Team, opponent_id)
    assert team is not None and opponent is not None  # FK로 보장
    players = session.exec(
        select(Player).where(col(Player.team_id).in_([team_id, opponent_id]))
    ).all()
    result = build_fortune(
        match.kickoff_at.astimezone(KST).date(),
        Side(team_id, team.name, [p for p in players if p.team_id == team_id]),
        Side(
            opponent_id, opponent.name, [p for p in players if p.team_id == opponent_id]
        ),
    )
    return FortunePublic(
        match_id=id,
        team_id=team_id,
        fortune_text=result.draft.fortune_text,
        cheer_tip=result.draft.cheer_tip,
        luck_score=result.draft.luck_score,
        grade=result.grade,
        lucky_players=result.lucky_players,
        caution_player=result.caution_player,
    )
