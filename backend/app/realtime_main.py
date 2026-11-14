"""공간·채팅 WebSocket을 API와 다른 프로세스로 띄울 때의 진입점.

같은 이미지에서 명령만 바꿔 띄우고, 프록시(Caddy)가 경로로 나눈다:
- `fastapi run app/realtime_main.py --app space_app`  ← /api/v1/space/* (공간·채팅)
- `fastapi run` (app/main.py)                        ← 나머지 API와 화면

워커 사이 전달은 Redis pub/sub이라 이 프로세스의 워커 수는 자유다.
로컬 개발은 `fastapi dev` 하나(app/main.py)가 전부 서빙한다.
"""

from fastapi import FastAPI

from app.api.routes import space
from app.core.config import settings

space_app = FastAPI(title=f"{settings.PROJECT_NAME} space", openapi_url=None)
space_app.include_router(space.router, prefix=settings.API_V1_STR)


# compose healthcheck가 API와 같은 경로를 쓰게 한다
@space_app.get(f"{settings.API_V1_STR}/utils/health-check/")
def health_check() -> bool:
    return True
