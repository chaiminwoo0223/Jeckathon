# CHEER 101 (해커톤)

스포츠 관람 기록 + 응원 커뮤니티 + 데시벨 대결. 기반은 full-stack-fastapi-template(FastAPI·SQLModel·Postgres / React·TanStack·shadcn).

- 명세 정본: [docs/cheer101-spec.md](docs/cheer101-spec.md). 데이터 모델·API 경로·비즈니스 규칙은 여기서 찾는다. 명세와 다르게 구현해야 하면 명세 파일을 같은 커밋에서 고친다.
- 실행 명령: [development.md](development.md) (`docker compose up -d db mailpit redis`, `uv run fastapi dev`, `bun run dev`).
- 범위: 명세 §6의 코어 → 양념 → 스트레치 순. 데모 시나리오는 명세 §7이고, 그 흐름이 돌아가는 게 완료 기준이다.

## 작업 공간

한 사람(한 에이전트)은 자기 영역의 파일만 고친다. 다른 영역이 필요하면 그 담당에게 요청한다.

| 역할 | 명세 범위 | 소유 파일 |
|---|---|---|
| BE-1 | 모델 User·UserSetting·Team·UserTeam·Match·CheerRecord·Badge·UserBadge·PointTransaction, 인증 스텁, §4.1–4.3(`/me/badges`·`/me/points` 제외), 경기 종료 정산(포인트·요정·배지 평가), 시드 | `backend/app/api/routes/{login,users,teams,matches,me,admin}.py`, `backend/app/initial_data.py`, `backend/app/services/settlement.py` |
| BE-2 | 모델 Community·CommunityMember·Battle·BattleRecord, §4.4–4.6, `/me/badges`·`/me/points` 조회, 커뮤니티 채팅 | `backend/app/api/routes/{communities,battles,rankings,rewards,chat,space}.py`, `backend/app/services/{battle,space}.py` |
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
- 채팅은 같은 FastAPI 앱의 WebSocket 엔드포인트 하나다(별도 소켓 서버 없음). 프론트 연동은 아래 "실시간 채팅 (프론트 연동)"을 따른다.

## 실시간 채팅 (프론트 연동)

백엔드 구현: `backend/app/api/routes/chat.py`(BE-2). 프론트 `frontend/src/cheer/components/live-chat.tsx`는 아직 로컬 상태 데모라 다른 사람 메시지가 안 온다. 아래대로 붙인다.

- 주소: `WS /api/v1/chat/rooms/{roomId}/ws?token=<access_token>`. `roomId`는 1 또는 2(고정). 브라우저 WebSocket은 헤더를 못 붙여서 토큰을 쿼리로 넘긴다. 호스트는 `VITE_API_URL`의 `http`를 `ws`로 바꿔 쓴다(HTTPS면 `wss`가 된다).
- 토큰: `POST /api/v1/login/access-token`이 주는 `access_token`(localStorage `access_token`). 지금 `/cheer/login`은 백엔드를 부르지 않으므로 이 토큰이 없다.
- 거부: 토큰이 없거나 틀리면, 방 번호가 1·2가 아니면 연결 전에 끊긴다(close code 1008).
- 보내기: 텍스트 그대로 `ws.send(text)`. 서버가 앞뒤 공백을 지우고 500자로 자르며 빈 문자열은 버린다.
- 받기: JSON `{room_id, user_id, name, text, sent_at}`. `name`은 닉네임(`User.display_nickname`, 비어 있으면 이메일 앞부분). 내가 보낸 것도 서버가 되돌려 주므로 화면에 직접 추가하지 않는다(중복된다). 내 메시지인지는 `user_id === JWT payload의 sub`로 가린다.
- 순서: 같은 방의 모든 사람이 같은 순서로 받는다(4명 동시 전송으로 확인). `sent_at`은 받은 순서대로 증가한다.
- 입장 직후 그 방의 최근 50개가 먼저 온다. DB에 저장하지 않으므로 서버를 재시작하면 사라진다.
- 접속자 수(화면의 "14명")는 백엔드에 아직 없다.
- 워커 수 제한 없음. 배포는 `fastapi run --workers 4`라 연결이 워커 4개에 흩어지는데, 메시지는 Postgres LISTEN/NOTIFY 버스(`backend/app/services/realtime.py`)로 모든 워커에 퍼진다. Redis는 쓰지 않는다. 다른 실시간 기능도 `bus.subscribe`·`bus.publish`를 쓴다(메시지 하나 8000바이트 미만).

```ts
const base = (import.meta.env.VITE_API_URL || location.origin).replace(/^http/, "ws")
const ws = new WebSocket(`${base}/api/v1/chat/rooms/${room}/ws?token=${localStorage.getItem("access_token")}`)
ws.onmessage = (e) => setMessages((prev) => [...prev, JSON.parse(e.data)])
// 보내기: ws.send(text)  (화면에 직접 추가하지 않음)
```

## 커뮤니티 공간 (메타버스, 프론트 연동)

백엔드: `backend/app/api/routes/space.py`, `backend/app/services/space.py`(BE-2). 채팅은 위 채팅 WS를 그대로 쓰고, 공간은 누가 어디 서 있는지와 이모트만 다룬다.

- 주소: `WS /api/v1/communities/{community_id}/space/ws?token=<access_token>`. `community_id`는 `GET /communities/today`의 `id`(UUID). 토큰·호스트는 채팅과 같다.
- 거부: 토큰이 틀리거나 커뮤니티가 없으면 연결 전에 끊긴다(close code 1008). 이때는 재연결하지 말고 로그인으로 보낸다.
- 좌표: 칸(grid). 원점 왼쪽 위, `x` 0..19, `y` 0..11 정수(크기는 snapshot `room.w`·`room.h`). 화면은 칸을 컨테이너 크기에 맞춰 늘리고, 칸 이동은 CSS `transition`으로 부드럽게 한다.
- 받기(server→client), JSON `type`으로 가른다:
  - `snapshot` (연결 직후 한 번): `{"type":"snapshot","v":1,"me":"<내 user_id>","room":{"id":"<community_id>","w":20,"h":12},"users":[{"user_id","name","avatar_url","x","y"}]}`. 받으면 사람 목록을 통째로 바꾼다.
  - `join`: `{"type":"join","user":{…users 한 칸…}}`. 이미 있는 사람이면 덮어쓴다(같은 사람이 탭을 더 연 경우).
  - `leave`: `{"type":"leave","user_id"}`. 그 사람의 마지막 탭이 닫혀야 온다.
  - `moves`: `{"type":"moves","p":{"<user_id>":[x,y],…}}`. 서버가 0.1초마다 그 사이 움직인 사람의 마지막 위치만 모아 보낸다(연결당 최대 10프레임/s, 이동이 화면에 뜨기까지 평균 약 50ms). 내 이동도 여기 들어온다(범위 밖 값은 잘려서). 목록에 없는 `user_id`는 무시한다(`leave` 직후 늦게 온 위치).
  - `emote`: `{"type":"emote","user_id","emote"}`. 말풍선·애니메이션으로 잠깐 보여 준다(저장 안 함).
  - `pong`, `error`(`{"type":"error","code":"bad_message"}`).
- 보내기(client→server): `{"type":"move","x":7,"y":4}`(탭할 때만, 초당 10개 넘는 건 서버가 버린다), `{"type":"emote","emote":"clap"}`(`clap`·`cheer`·`wave`·`fire`, 1초에 1번), `{"type":"ping"}`(25초마다. 60초 동안 아무것도 안 보내면 다른 사람 화면에서 사라진다).
- 재연결: 끊기면 1·2·4…최대 10초 간격으로 다시 붙고, 새 snapshot으로 통째로 바꾼다. `StrictMode` 개발 모드의 이중 연결은 서버가 탭 수로 세서 문제없다(effect cleanup에서 `ws.close()`).
- `frontend/src/client/`(생성 클라이언트)에는 WS가 안 들어가므로 메시지 타입은 프론트가 직접 쓴다. 로컬에서 vite proxy로 붙이면 `/api` 항목에 `ws: true`가 있어야 한다.
- 상태는 Redis에만 있다(재시작하면 비어도 된다). 로컬은 `docker compose up -d redis`, 설정은 `REDIS_URL`(기본 `redis://localhost:6379/0`). Redis가 없어도 서버는 뜨고 이 WS만 실패한다.

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

## 배포

- `main`에 합쳐지면 GitHub Actions `Deploy (home server)`가 홈서버의 self-hosted runner에서 `deploy/home/deploy.sh`를 돌려 https://cheer101.infoedu.co.kr 에 올린다. 다시 올리려면 Actions 탭에서 Run workflow.
- 화면은 백엔드 이미지에 빌드돼 같은 주소로 나간다(`VITE_API_URL` 비움). 배포마다 migration·시드(`prestart.sh`)가 돈다. 실패하면 워크플로가 빨간불이고 로그 끝에 prestart 로그가 찍힌다.
- 운영 비밀값(SECRET_KEY, DB·superuser 비밀번호, AI_API_KEY)은 서버 파일에만 있다. 바꿀 일이 있으면 배포 담당(SonAIengine)에게.
- `deploy/`, `.github/`는 배포 담당 영역이다.
- 커뮤니티 공간 WS는 Redis가 있어야 한다. 운영 `deploy/home/compose.yml`에 `redis:8-alpine` 서비스와 backend 환경변수 `REDIS_URL: redis://redis:6379/0`이 필요하다(배포 담당에게 요청, 루트 `compose.yml`의 redis 서비스가 예시).

## Git

- 브랜치: `be1/<주제>`, `be2/<주제>`, `ai/<주제>`, `fe/<주제>`. 작게 자주 main에 합친다.
- 커밋 전에 자기 영역 검사를 돌린다: 백엔드 `cd backend && uv run ruff check app --fix && uv run ruff format app`, 프론트 `bun run lint`. (템플릿 `scripts/lint.sh`는 mypy·ty까지 돌아 느리다. 머지 전 한 번만.)
- `.env`는 git에 올라가 있다. API 키 같은 비밀값은 `.env`에 넣지 말고 셸 환경변수나 git에 없는 파일로 둔다.
