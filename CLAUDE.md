# CHEER 101 (해커톤)

스포츠 관람 기록 + 응원 커뮤니티 + 데시벨 대결. 기반은 full-stack-fastapi-template(FastAPI·SQLModel·Postgres / React·TanStack·shadcn).

- 명세 정본: [docs/cheer101-spec.md](docs/cheer101-spec.md). 데이터 모델·API 경로·비즈니스 규칙은 여기서 찾는다. 명세와 다르게 구현해야 하면 명세 파일을 같은 커밋에서 고친다.
- 실행 명령: [development.md](development.md) (`docker compose up -d db mailpit`, `uv run fastapi dev`, `bun run dev`).
- 범위: 명세 §6의 코어 → 양념 → 스트레치 순. 데모 시나리오는 명세 §7이고, 그 흐름이 돌아가는 게 완료 기준이다.

## 작업 공간

한 사람(한 에이전트)은 자기 영역의 파일만 고친다. 다른 영역이 필요하면 그 담당에게 요청한다.

| 역할 | 명세 범위 | 소유 파일 |
|---|---|---|
| BE-1 | 모델 User·UserSetting·Team·UserTeam·Match·CheerRecord·Badge·UserBadge·PointTransaction, 인증 스텁, §4.1–4.3(`/me/badges`·`/me/points` 제외), 경기 종료 정산(포인트·요정·배지 평가), 시드 | `backend/app/api/routes/{login,users,teams,matches,me,admin}.py`, `backend/app/initial_data.py`, `backend/app/services/settlement.py` |
| BE-2 | 모델 Community·CommunityMember·Battle·BattleRecord, §4.4–4.6, `/me/badges`·`/me/points` 조회, 커뮤니티 채팅 | `backend/app/api/routes/{communities,battles,rankings,rewards,chat}.py`, `backend/app/services/battle.py` |
| AI | Fortune, §4.7 운세, (양념) 기록 한 줄 평. 모델 API 제공자는 AI 담당이 고른다 | `backend/app/api/routes/fortune.py`, `backend/app/ai/` |
| FE | 명세 §5 화면 전부, Web Audio 데시벨 측정 | `frontend/` 전체 (생성 파일 제외) |

포인트 지급 함수는 BE-1이 `services/settlement.py`에 하나 두고, BE-2의 대결 TOP3 지급도 그 함수를 호출한다(지급 로직 한 곳).

## 공유 파일 규칙

여러 역할이 함께 고치는 파일. 충돌이 여기서 난다.

- `backend/app/models.py`: 역할별 구역 주석(`# --- BE-1 ---`, `# --- BE-2 ---`, `# --- AI ---`) 아래에만 추가한다. 다른 구역의 모델을 바꿔야 하면 그 담당에게 요청한다.
- `backend/app/api/main.py`: `include_router` 한 줄 추가만 한다.
- Alembic(`backend/app/alembic/versions/`): 리비전 만들기 전에 main을 pull하고 `cd backend && uv run alembic heads`가 한 줄인지 본다. 두 줄이면 `uv run alembic merge heads -m merge`를 먼저 한다. 생성은 `uv run alembic revision --autogenerate -m "<무엇>"`.
- 생성 파일은 손으로 고치지 않는다: `frontend/src/client/`(백엔드 스키마에서 생성), `frontend/src/routeTree.gen.ts`(라우터 플러그인이 생성).

## API 계약

- 경로는 명세 §4 그대로, prefix `/api/v1`(템플릿 `settings.API_V1_STR`).
- JSON 필드는 snake_case로 쓴다(명세 예시의 camelCase `totalPoints` → `total_points`). 프론트 클라이언트는 `case: "preserve"`라 이름이 그대로 넘어간다.
- 백엔드가 응답 스키마를 바꾸고 push하면 FE는 pull 후 루트에서 `bash scripts/generate-client.sh`로 클라이언트를 다시 만든다(서버 실행 불필요, `uv sync` 필요).
- 채팅을 뺀 실시간은 폴링이다(명세 §0). 프론트는 TanStack Query `refetchInterval: 2000`~`3000`, `retry: 1`. 백엔드는 스케줄러 없이 조회 시점에 상태를 전환한다(대결 지연 정산, 명세 §4.6).
- 채팅도 폴링으로 시작한다. WebSocket이 필요해지면 같은 FastAPI 앱의 `@router.websocket` 엔드포인트 하나로 붙인다(별도 소켓 서버 없음).

## 키와 환경 파일

- `.env`, `frontend/.env`: git에 올라가 있고 템플릿 기본값(`changethis`)을 그대로 쓴다. 저장소가 PUBLIC이라 실제 비밀값은 여기 넣지 않는다.
- `.env.local`(루트, gitignore): 팀이 메신저로 직접 주고받는 비밀값. 백엔드가 `.env` 다음에 읽어 덮어쓴다. AI 키는 `AI_API_KEY=...`로 넣고 코드에서는 `settings.AI_API_KEY`로 읽는다.
- `AI_API_KEY`가 없거나 호출이 실패하면 운세 API는 고정 문구로 응답한다(데모가 키 없이도 돈다).

## 함정

- migration과 시드는 자동으로 돌지 않는다. 모델이나 `initial_data`를 바꾸면 `cd backend && uv run bash scripts/prestart.sh`.
- 기존 테이블에 NOT NULL 칼럼을 더하면 `server_default`가 있어야 upgrade가 된다: `Field(default=0, sa_column_kwargs={"server_default": "0"})`. superuser 행이 이미 있다.
- 시드는 `backend/app/core/db.py`의 `init_db` 끝에, superuser처럼 "조회 후 없으면 삽입"으로 넣는다.
- 템플릿 Item 모델은 지우지 않는다(백·프 12곳이 엮임). 메뉴만 `frontend/src/components/Sidebar/AppSidebar.tsx`에서 뺀다.
- 휴대폰 시연: 마이크(getUserMedia)는 HTTPS에서만 된다. `cloudflared tunnel --url http://localhost:5173`으로 열고, vite `server.proxy`로 `/api`를 8000에 넘기고 `VITE_API_URL`을 비운다. 터널 도메인은 vite `server.allowedHosts`에 추가한다.
- 데시벨: Web Audio 값은 dBFS(≤0)다. 명세의 110dB는 `dBFS + 고정 오프셋`인 게임용 값이고 실제 SPL이 아니다.

## Git

- 브랜치: `be1/<주제>`, `be2/<주제>`, `ai/<주제>`, `fe/<주제>`. 작게 자주 main에 합친다.
- 커밋 전에 자기 영역 검사를 돌린다: 백엔드 `cd backend && uv run ruff check app --fix && uv run ruff format app`, 프론트 `bun run lint`. (템플릿 `scripts/lint.sh`는 mypy·ty까지 돌아 느리다. 머지 전 한 번만.)
- `.env`는 git에 올라가 있다. API 키 같은 비밀값은 `.env`에 넣지 말고 셸 환경변수나 git에 없는 파일로 둔다.
