from typing import Any

from fastapi import APIRouter
from sqlmodel import col, select

from app.api.deps import SessionDep
from app.models import Team, TeamPublic, TeamsPublic

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/", response_model=TeamsPublic)
def read_teams(session: SessionDep) -> Any:
    """
    전체 팀 목록.
    """
    teams = session.exec(select(Team).order_by(col(Team.name))).all()
    return TeamsPublic(
        data=[TeamPublic.model_validate(t) for t in teams], count=len(teams)
    )
