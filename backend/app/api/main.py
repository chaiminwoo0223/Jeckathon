from fastapi import APIRouter

from app.api.routes import (
    admin,
    battles,
    chat,
    communities,
    items,
    login,
    matches,
    me,
    private,
    rewards,
    space,
    teams,
    users,
    utils,
)
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
api_router.include_router(teams.router)
api_router.include_router(matches.router)
api_router.include_router(me.router)
api_router.include_router(admin.router)
api_router.include_router(communities.router)
api_router.include_router(communities.match_router)
api_router.include_router(battles.router)
api_router.include_router(chat.router)
api_router.include_router(rewards.router)
api_router.include_router(space.router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
