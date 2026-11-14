import uuid
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from app.ai.fortune_seed import pick_fortune
from app.api.deps import SessionDep
from app.api.routes.matches import KST
from app.models import FortunePublic, Match, Team

router = APIRouter(prefix="/matches", tags=["fortune"])


@router.get("/{id}/fortune", response_model=FortunePublic)
def read_fortune(
    session: SessionDep,
    id: uuid.UUID,
    team_id: Annotated[uuid.UUID, Query()],
) -> Any:
    """
    경기 당일 응원팀 운세. 시드 문구 풀에서 (경기 날짜, 팀)으로 고정해 고른다.
    같은 날 같은 팀은 항상 같은 운세이고 DB에 저장하지 않는다(AI 연동은 후속).
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
    assert team is not None  # FK로 보장
    draft = pick_fortune(
        match.kickoff_at.astimezone(KST).date(), team_id, opponent_id, team.name
    )
    return FortunePublic(
        match_id=id,
        team_id=team_id,
        fortune_text=draft.fortune_text,
        cheer_tip=draft.cheer_tip,
        luck_score=draft.luck_score,
    )
