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
| BE-2 | 모델 Community·CommunityMember·Battle·BattleRecord, §4.4–4.6, `/me/badges`·`/me/points` 조회, 커뮤니티 채팅 | `backend/app/api/routes/{communities,battles,rankings,rewards,space}.py`, `backend/app/services/{battle,space}.py` |
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
- 채팅은 커뮤니티 공간 WebSocket의 메시지 종류(`chat`)다. 같은 FastAPI 앱 안, 워커 사이는 Redis pub/sub(별도 소켓 서버 없음). 프론트 연동은 아래 "커뮤니티 공간·채팅"을 따른다.

## 포인트·배지 (프론트 연동)

- 대결 결과 `GET /battles/{id}/result`에 `top3[].points`(그 사람이 받은 포인트)와 `my_points`(내가 받은 포인트, TOP3 밖이면 0)가 생겼다. 포인트는 대결 종료 후 첫 조회 때 서버가 지급한다.
- 새 엔드포인트: `GET /me/points?page=&size=`(포인트 내역, 최신순, `total_points` 포함), `GET /me/badges`(획득 배지, 최근 순). 응답 형태는 명세 §4.3 "구현 메모 (BE-2)".
- 이 변경을 받은 뒤 루트에서 `bash scripts/generate-client.sh`로 클라이언트를 다시 만든다.

## 커뮤니티 공간·채팅 (메타버스, 프론트 연동)

백엔드: `backend/app/api/routes/space.py`, `backend/app/services/space.py`(BE-2). 커뮤니티(경기 방)마다 소켓 하나로 누가 어디 서 있는지·이모트·채팅을 다룬다. 예전 `WS /chat/rooms/{roomId}/ws`(고정 방 1·2)는 없앴다. 프론트 `live-chat.tsx`도 이 소켓의 `chat`을 쓴다.

- 주소: `WS /api/v1/communities/{community_id}/space/ws?token=<access_token>`. `community_id`는 `GET /communities/today`의 `id`(UUID). 토큰은 `POST /api/v1/login/access-token`(또는 `/auth/login`)의 `access_token`을 쿼리로 넘긴다(브라우저 WebSocket은 헤더를 못 붙인다). 호스트는 `VITE_API_URL`의 `http`를 `ws`로 바꿔 쓴다(HTTPS면 `wss`).
- 거부: 토큰이 틀리거나, 그 커뮤니티에 입장(`POST /communities/{id}/join`)하지 않았으면 연결 전에 끊긴다(close code 1008). 이때는 재연결하지 않는다. 먼저 join이 성공해야 공간에 붙는다.
- 좌표: 칸(grid). 원점 왼쪽 위, `x` 0..19, `y` 0..11 정수(크기는 snapshot `room.w`·`room.h`). 화면은 칸을 컨테이너 크기에 맞춰 늘리고, 칸 이동은 CSS `transition`으로 부드럽게 한다.
- 받기(server→client), JSON `type`으로 가른다:
  - `snapshot` (연결 직후 한 번): `{"type":"snapshot","v":1,"me":"<내 user_id>","room":{"id":"<community_id>","w":20,"h":12},"users":[{"user_id","name","avatar_url","x","y"}],"chat":[…chat 메시지, 오래된 것부터 최근 50개…]}`. 받으면 사람 목록과 채팅 목록을 통째로 바꾼다.
  - `join`: `{"type":"join","user":{…users 한 칸…}}`. 이미 있는 사람이면 덮어쓴다(같은 사람이 탭을 더 연 경우).
  - `leave`: `{"type":"leave","user_id"}`. 그 사람의 마지막 탭이 닫혀야 온다.
  - `moves`: `{"type":"moves","p":{"<user_id>":[x,y],…}}`. 서버가 0.1초마다 그 사이 움직인 사람의 마지막 위치만 모아 보낸다(연결당 최대 10프레임/s, 이동이 화면에 뜨기까지 평균 약 50ms). 내 이동도 여기 들어온다(범위 밖 값은 잘려서). 목록에 없는 `user_id`는 무시한다(`leave` 직후 늦게 온 위치).
  - `emote`: `{"type":"emote","user_id","emote"}`. 말풍선·애니메이션으로 잠깐 보여 준다(저장 안 함).
  - `chat`: `{"type":"chat","user_id","name","text","sent_at"}`. `name`은 닉네임(`User.display_nickname`). 내가 보낸 것도 이걸로 돌아오므로 화면에 직접 추가하지 않는다(중복된다). 같은 방의 모든 사람이 같은 순서로 받는다(워커 4개·4명 동시 전송으로 확인). 순서는 도착 순서이고 `sent_at`은 표시용이라 워커가 다르면 앞뒤가 아주 조금 뒤바뀔 수 있다.
  - `pong`, `error`(`{"type":"error","code":"bad_message"}`).
- 보내기(client→server): `{"type":"move","x":7,"y":4}`(탭할 때만, 초당 10개 넘는 건 서버가 버린다), `{"type":"emote","emote":"clap"}`(`clap`·`cheer`·`wave`·`fire`, 1초에 1번), `{"type":"chat","text":"…"}`(서버가 앞뒤 공백을 지우고 500자로 자르며 빈 글은 버린다), `{"type":"ping"}`(25초마다. 60초 동안 아무것도 안 보내면 다른 사람 화면에서 사라진다).
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
- 커뮤니티 공간·채팅 WS는 Redis로 워커(`--workers 4`) 사이를 잇는다. 운영 `deploy/home/compose.yml`에 `redis` 서비스(`redis:8-alpine`)와 backend 환경변수 `REDIS_URL: redis://redis:6379/0`이 있다. Redis가 없으면 서버는 뜨지만 이 WS가 모두 실패한다. 워커 수를 1로 줄일 필요는 없다.

## Git

- 브랜치: `be1/<주제>`, `be2/<주제>`, `ai/<주제>`, `fe/<주제>`. 작게 자주 main에 합친다.
- 커밋 전에 자기 영역 검사를 돌린다: 백엔드 `cd backend && uv run ruff check app --fix && uv run ruff format app`, 프론트 `bun run lint`. (템플릿 `scripts/lint.sh`는 mypy·ty까지 돌아 느리다. 머지 전 한 번만.)
- `.env`는 git에 올라가 있다. API 키 같은 비밀값은 `.env`에 넣지 말고 셸 환경변수나 git에 없는 파일로 둔다.
