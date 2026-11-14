# CHEER 101 — 기능 명세서

> 스포츠 경기 관람 기록 + 응원 커뮤니티 + 데시벨 대결 서비스. 해커톤 산출물 기준으로 백엔드가 바로 개발에 착수할 수 있도록 **데이터 모델 / API / 비즈니스 규칙** 중심으로 정리.

## 0. 핵심 아키텍처 결정

- **채팅·커뮤니티 공간 외 실시간 미사용.** 데시벨 대결·랭킹 등 나머지는 **REST + 폴링(2~3초 간격)** 과 DB 조회로 처리한다. 채팅과 커뮤니티 공간(메타버스: 접속자 위치·이모트)만 WebSocket이고, 별도 소켓 서버 없이 같은 FastAPI 앱 안에 둔다. 공간 상태와 워커 간 전달은 Redis.
- **데시벨 대결 = 핫시트/동시참여 혼합.** 측정은 전적으로 **클라이언트(Web Audio API)** 에서 수행하고, 서버는 점수(peak dB)만 받아 저장·집계한다. 서버는 음성을 다루지 않는다.
- **경기 일정 데이터는 시드(seed) 테이블로 적재.** 외부 API 연동(football-data.org 등)은 시간 남으면 스트레치. 데모 안정성 위해 샘플 경기 데이터를 DB에 미리 넣는다.
- 인증은 해커톤 범위에서 **소셜 로그인 스텁 or 단순 토큰**으로 최소화. (아래 명세는 `userId`를 인증 컨텍스트에서 획득한다고 가정)

## 1. 핵심 개념 & 용어

| 용어 | 설명 |
| --- | --- |
| 응원 기록(CheerRecord) | 유저가 "이 경기를 보고 이 팀을 응원했다"는 기록. 경기 종료 시 승/무/패 확정 |
| 승리요정 / 패배요정 | 승률 기준으로 판정되는 유저 칭호. 닉네임 앞에 붙음 |
| 커뮤니티(Community) | 경기 1개당 1개 생성되는 응원방 |
| 데시벨 대결(Battle) | 커뮤니티 안에서 열리는 타임어택 응원 게임 (최대 5명) |
| 포인트(Point) | 경기 결과·데시벨 TOP3로 적립되는 재화 |
| 운세(Fortune) | 경기 당일 응원팀 기준 운세. 그날 두 팀 선수들의 생년월일로 6단계 등급(대길·중길·소길·소흉·중흉·대흉)과 선수 몇 명을 뽑는다. 문구는 시드 풀, AI 생성은 후속 |

## 2. 데이터 모델

### 2.1 User (유저)

```
User {
  id              PK
  email           string
  nickname        string            // "뚜비응원단"
  bio             string            // 한 줄 소개
  profileImageUrl string?
  level           int    default 1  // 누적 포인트 기반 (3.4 참조)
  totalPoints     int    default 0
  createdAt       datetime
}
```

### 2.2 UserSetting (유저 설정)

```
UserSetting {
  userId                PK/FK
  notifyMatchSchedule   bool default true   // 경기 일정 알림
  notifyCommunityInvite bool default true   // 커뮤니티 초대 알림
  notifyRankingReward   bool default true   // 랭킹/보상 알림
  notifyService         bool default false  // 서비스 소식/이벤트
  autoJoinCommunity     bool default true   // 경기 당일 자동 입장
  micPermission         bool default false  // 데시벨 마이크 권한
  rankingPublic         bool default true   // 랭킹 공개 여부
}
```

### 2.3 Team (팀)

```
Team {
  id        PK
  name      string   // "LG"
  fullName  string   // "LG 트윈스"
  logoUrl   string
  league    string   // "KBO리그"
}
```

### 2.4 UserTeam (응원하는 팀, M:N)

```
UserTeam {
  userId  FK
  teamId  FK
  PK(userId, teamId)
}
```

### 2.5 Match (경기)

```
Match {
  id           PK
  homeTeamId   FK
  awayTeamId   FK
  league       string
  kickoffAt    datetime          // 경기 시작 시각
  status       enum[SCHEDULED, LIVE, FINISHED]
  homeScore    int?              // 종료 시 채워짐
  awayScore    int?
  finishedAt   datetime?
}
```

### 2.6 CheerRecord (응원 기록) — 핵심 테이블

```
CheerRecord {
  id             PK
  userId         FK
  matchId        FK
  cheeredTeamId  FK                // 응원한 팀 (home/away 중 하나)
  result         enum[PENDING, WIN, DRAW, LOSE]  // 경기 종료 시 확정
  pointsEarned   int default 0
  createdAt      datetime
  UNIQUE(userId, matchId)          // 한 경기당 1기록
}
```

### 2.7 Community (커뮤니티) & CommunityMember

```
Community {
  id         PK
  matchId    FK UNIQUE          // 경기당 1개
  createdAt  datetime
}

CommunityMember {
  communityId FK
  userId      FK
  joinedAt    datetime
  PK(communityId, userId)
}
```

### 2.8 Battle (데시벨 대결) & BattleRecord

```
Battle {
  id          PK
  communityId FK
  status      enum[WAITING, ONGOING, FINISHED]
  durationSec int default 60
  startedAt   datetime?
  endsAt      datetime?          // startedAt + durationSec
  maxPlayers  int default 5
}

BattleRecord {
  id        PK
  battleId  FK
  userId    FK
  peakDb    float                // 유저별 최고 데시벨 (갱신 시 max 유지)
  updatedAt datetime
  UNIQUE(battleId, userId)
}
```

### 2.9 Badge & UserBadge

```
Badge {
  id          PK
  code        string UNIQUE     // "VICTORY_FAIRY"
  name        string            // "승리요정"
  description string            // "승률 60% 이상"
  iconUrl     string
}

UserBadge {
  userId      FK
  badgeId     FK
  acquiredAt  datetime
  PK(userId, badgeId)
}
```

### 2.10 PointTransaction (포인트 내역)

```
PointTransaction {
  id        PK
  userId    FK
  amount    int                 // +100, +50, +30 ...
  reason    enum[MATCH_RESULT, DECIBEL_TOP3]
  relatedId string?             // matchId or battleId
  createdAt datetime
}
```

### 2.11 Fortune (운세, AI 생성 캐시 — AI 연동 때 사용, 지금은 비어 있음)

```
Fortune {
  id          PK
  matchId     FK
  teamId      FK
  date        date              // 경기 당일
  fortuneText string            // "흐름이 좋은 날이에요! ..."
  cheerTip    string            // "7회 이후 불펜 운용을 주목하세요"
  luckScore   int               // 0~100
  UNIQUE(matchId, teamId, date)
}
```

### 2.12 Player (선수, 운세 입력용 — KBO 공개 명단 스냅샷)

```
Player {
  id         PK
  kboId      int UNIQUE         // KBO 선수 번호. 시드 upsert 키
  teamId     FK
  name       string
  position   string             // 투수/포수/내야수/외야수 (빈 값 허용)
  backNumber string?            // 등번호. 3자리(육성)·null은 운세 후보에서 제외
  birthDate  date               // 운세의 핵심 입력. 응답에는 birthYear만 내린다
}
```

- 출처 `backend/app/seed/kbo_people_2026.json`(koreabaseball.com, 수집일 2026-11-14, 팀당 ~100명 선수만 적재). 1군 엔트리·라인업 데이터는 없다.

## 3. 비즈니스 규칙 (계산 로직)

### 3.1 승률 / 패배율

- 분모는 **무승부 제외** (승 + 패). 목업 기준: 42경기 중 승28·패13·무3 → 승률 = 28 / (28+13) = **68%**.
- `winRate = wins / (wins + losses)` (승+패 = 0이면 0%)
- `loseRate = losses / (wins + losses)`

### 3.2 요정 판정 (유저 칭호)

- `winRate >= 0.6` → **승리요정** (닉네임 앞 "승리요정 {nickname}")
- `loseRate >= 0.3` → **패배요정**
- 둘 다 해당되면 승리요정 우선. 둘 다 아니면 **중립요정**.
- 판정은 응원 기록이 확정될 때마다 재계산.

### 3.3 포인트 지급

| 사유 | 조건 | 지급 |
| --- | --- | --- |
| 경기 결과 | 승리 | +100P |
| 경기 결과 | 무승부 | +50P |
| 경기 결과 | 패배 | +30P |
| 데시벨 대결 | 1등 | +100P |
| 데시벨 대결 | 2등 | +50P |
| 데시벨 대결 | 3등 | +30P |

- 모든 지급은 `PointTransaction`에 기록하고 `User.totalPoints` 갱신.

### 3.4 레벨 (제안)

- `level = floor(totalPoints / 300) + 1` (해커톤용 단순 공식, 조정 가능)

### 3.5 배지 획득 조건 (평가 트리거: 기록 확정 / 대결 종료 후)

| code | name | 조건 |
| --- | --- | --- |
| VICTORY_FAIRY | 승리요정 | 승률 60% 이상 |
| DEFEAT_FAIRY | 패배요정 | 패배율 30% 이상 |
| WIN_STREAK_3 | 연승러 | 3연승 |
| DECIBEL_MASTER | 데시벨 마스터 | 최고 측정 110dB 이상 |
| STEADY_FAN | 꾸준한 응원단 | 10경기 이상 기록 |

## 4. API 명세

> 기본 prefix `/api/v1`. 인증은 헤더 토큰 → `userId` 컨텍스트 주입 가정. 응답은 JSON.

### 4.1 인증 / 유저

| Method | Path | 설명 |
| --- | --- | --- |
| GET | /auth/check-username?username= | 아이디 중복 체크. `{username, available}` |
| POST | /auth/signup | 아이디·비밀번호 가입. `{username, password}` → `{accessToken, user}` (중복이면 409) |
| POST | /auth/login | 아이디·비밀번호 로그인. `{username, password}` → `{accessToken, user}` |
| GET | /me | 내 프로필 + 통계 요약 (요정 타입, 승률, 레벨, 포인트, 응원팀) |
| PATCH | /me/profile | `{nickname?, bio?, profileImageUrl?}` |
| GET | /me/settings | 설정 조회 |
| PATCH | /me/settings | 설정 토글 일부 업데이트 |
| GET | /me/teams | 응원하는 팀 목록 |
| POST | /me/teams | `{teamId}` 추가 |
| DELETE | /me/teams/{teamId} | 응원팀 제거 |

**구현 메모 (BE-1)**

- 로그인은 아이디·비밀번호뿐이다(소셜·이메일 없음). 아이디는 영문·숫자·밑줄 4~20자이고 대소문자를 구분하지 않는다(소문자로 저장). 비밀번호는 4자 이상. 응답은 `{access_token, token_type, user}`이고 이후 요청은 `Authorization: Bearer`로 보낸다.
- 로그인 아이디는 별도 칼럼 없이 `email` 칼럼에 합성해 저장한다(`{username}@users.cheer101.example.com`, 메일은 보내지 않는다). 아이디 중복 체크는 이 칼럼의 unique로 한다. 그래서 `/me`·로그인 응답의 `user`에는 `email`·`username`이 없다. `User`의 이름 필드는 `nickname` 하나뿐이고 템플릿의 `full_name`은 제거했다. 관리자 계정은 템플릿의 `/login/access-token`(이메일)으로 로그인한다.
- 로그인 실패는 아이디가 없든 비밀번호가 틀리든 같은 400 응답이다.
- `POST /me/teams`, `DELETE /me/teams/{teamId}`는 갱신된 응원팀 목록 `{data, count}`를 돌려준다. 이미 있는 팀 추가는 그대로 두고, 없는 팀 삭제는 404다.
- `GET /me`와 `GET /me/stats`의 통계는 확정된 응원 기록(PENDING 제외)으로 센다. `total`은 승+무+패다.
- `nickname`이 비어 있으면 이름, 그것도 없으면 이메일 앞부분으로 채워 응답한다.

**GET /me 응답 예시**

```json
{
  "id": 1,
  "nickname": "뚜비응원단",
  "fairyType": "VICTORY",
  "fairyLabel": "승리요정 뚜비응원단",
  "level": 12,
  "totalPoints": 3820,
  "stats": { "total": 42, "win": 28, "draw": 3, "lose": 13,
             "winRate": 0.68, "loseRate": 0.32 },
  "teams": [{ "id": 3, "name": "LG" }, { "id": 4, "name": "두산" }]
}
```

### 4.2 팀 / 경기 일정 (캘린더)

| Method | Path | 설명 |
| --- | --- | --- |
| GET | /teams | 전체 팀 목록 |
| GET | /matches?month=YYYY-MM | 월별 경기 (캘린더 렌더용). 날짜별 그룹 |
| GET | /matches/today | 오늘 경기 목록 |
| GET | /matches/{id} | 경기 상세 (팀, 시각, 상태, 스코어) |

### 4.3 응원 설정 / 기록

| Method | Path | 설명 |
| --- | --- | --- |
| POST | /matches/{id}/cheer | 응원팀 선택. `{cheeredTeamId}` → CheerRecord(PENDING) 생성/수정 |
| GET | /me/records?page= | 내 응원 기록 리스트 (최근 경기, 결과, 포인트) |
| GET | /me/stats | 시즌 통계 (도넛용: win/draw/lose 수, 승률) |
| GET | /me/badges | 획득 배지 목록 |
| GET | /me/points?page= | 포인트 내역 |
| GET | /me/share-card | SNS 공유 카드 데이터 (승률, 경기수, 요정, 최애팀) |

**구현 메모 (BE-1)**

- `POST /matches/{id}/cheer`: `cheeredTeamId`는 그 경기의 홈팀 또는 원정팀이어야 한다(아니면 400). 종료(FINISHED)된 경기는 409다. 이미 정산으로 확정된 기록도 수정할 수 없다(409). 같은 경기에 다시 보내면 새 기록이 아니라 응원팀만 바뀐다.
- `GET /me/records?page=&size=`: 1부터 시작하는 `page`, 기본 `size` 20(최대 100). 최근 경기 순이고 각 항목에 `match`(팀 정보 포함)가 들어 있다. 응답은 `{data, count, page, size}`이고 `count`는 전체 기록 수다.

- `GET /me/share-card`: 닉네임·프로필 이미지, 요정(`fairy_type`·`fairy_label`), `stats`(`total`이 경기수, `/me`와 같은 규칙), `favorite_team`을 돌려준다(로그인 필요). **최애팀**은 응원 기록(진행 전 포함)에서 가장 많이 응원한 팀이고, 같은 횟수면 가장 최근에 응원한 팀이다. 응원 기록이 없으면 응원팀 설정(`/me/teams`)의 첫 팀, 그것도 없으면 `null`이다. 카드 이미지는 프론트가 그린다.

**구현 메모 (BE-2)**

- `GET /me/points?page=&size=`: 1부터 시작하는 `page`, 기본 `size` 20(최대 100). 최신순이고 로그인이 필요하다. 응답은 `{data: [{id, amount, reason, related_id, created_at}], count, page, size, total_points}`이고 `count`는 전체 내역 수다. `reason`은 `MATCH_RESULT`(`related_id`=matchId) 또는 `DECIBEL_TOP3`(`related_id`=battleId)다.
- `GET /me/badges`: 획득한 배지를 최근 획득 순으로 돌려준다(로그인 필요). 응답은 `{data: [{code, name, description, icon_url, acquired_at}], count}`다.

**경기 종료 처리 (내부 배치/관리자 트리거)**

- `PATCH /admin/matches/{id}/finish` `{homeScore, awayScore}` 호출 시:
  1. Match status=FINISHED, 스코어 저장
  2. 해당 경기의 PENDING CheerRecord 전부 result 확정 (응원팀 기준 승/무/패)
  3. 결과별 포인트 지급 + PointTransaction 기록
  4. 유저별 승률/요정/배지 재평가
- 데모에서는 이 엔드포인트로 "경기 끝남"을 수동 발동해 결과 화면을 시연.
- 구현 메모 (BE-1): superuser 전용이고 한 트랜잭션으로 처리한다(중간에 실패하면 전부 되돌린다). 이미 종료된 경기는 409이며, 시작 전(SCHEDULED) 경기도 바로 종료할 수 있다. 응답은 `{match, settled, win, draw, lose}`다.
- 포인트는 `services/settlement.py`의 `grant_points` 한 곳에서만 지급한다(대결 TOP3도 호출). 같은 (유저, 사유, 대상)에는 한 번만 지급되고(DB unique), 레벨은 지급할 때 `total_points // 300 + 1`로 다시 계산한다.
- 배지는 한 번 얻으면 회수하지 않는다(요정 칭호는 조회 때마다 계산하므로 바뀔 수 있다). 3연승은 확정된 최근 3경기가 모두 승리일 때이며 무승부는 연승을 끊는다. 10경기는 확정된 기록 기준이다. 데시벨 마스터는 대결 종료 후 `evaluate_badges(..., peak_db=)`로 평가한다.

### 4.4 커뮤니티

| Method | Path | 설명 |
| --- | --- | --- |
| GET | /communities/mine | 내가 응원 신청한 경기(종료 전)를 KST 날짜별로 묶은 목록 + 경기별 입장 가능 여부 (커뮤니티 홈) |
| GET | /communities/today | 오늘의 커뮤니티 (대표 경기 1개 + 메타) |
| GET | /matches/{id}/community | 경기별 커뮤니티 정보 (멤버 수, 내 입장 여부) |
| POST | /communities/{id}/join | 입장 (초대장 → 입장). 입장 규칙은 아래 참고 |
| POST | /communities/{id}/leave | 나가기 |
| GET | /communities/{id}/members | 멤버 목록 (프로필, 요정 타입) |
| WS | /space/{communityId}/ws?token={JWT} | 커뮤니티 공간(메타버스, 3D 응원 스타디움)과 실시간 채팅을 한 소켓으로. 입장한 멤버만. 원형 경기장(반경 16.5) 위 접속자 위치·방향, 응원팀 유니폼, 말풍선·이모트, 채팅(최근 50개 Redis). DB 저장 없음. API와 다른 프로세스로 띄울 수 있다. 메시지 형식은 팀 CLAUDE.md "커뮤니티 공간·채팅" |

**입장 규칙**

- 응원 신청(§4.3 `POST /matches/{id}/cheer`)한 경기의 커뮤니티에만 입장할 수 있다.
- 입장은 **경기 시작(`kickoffAt`) 1시간 전부터 경기 종료(`FINISHED`)까지** 가능하다. 경기 상태는 자동으로 LIVE가 되지 않으므로(스케줄러 없음) 상태가 아니라 **시간**으로 판단한다: `now >= kickoffAt - 1시간 && status != FINISHED`.
- 이 판단은 서버가 하고 응답에 담는다(`enterOpensAt`, `canEnter`). 브라우저 시계에 의존하지 않고, 프론트는 `serverNow`로 카운트다운만 그린다. 버튼 비활성화만으로는 API 직접 호출을 막을 수 없으므로 `join`도 같은 규칙으로 서버에서 거절한다.
- `join` 거절: 입장 시간 전 → 403 `NOT_OPEN_YET`(`enterOpensAt` 포함), 응원 신청을 하지 않은 경기 → 403 `NOT_CHEERED`, 종료된 경기 → 409 `MATCH_FINISHED`. 이미 멤버면 그대로 성공한다(멱등).
- 커뮤니티는 경기당 1개이며, 필요할 때 처음 만든다(동시 요청이어도 중복 생성되지 않는다).
- `UserSetting.autoJoinCommunity`(경기 당일 자동 입장)는 이번 범위에서 연결하지 않는다.

**GET /communities/mine 응답 예시** (로그인 필요)

```json
{
  "serverNow": "2026-11-14T15:30:00+09:00",
  "count": 3,
  "days": [
    { "date": "2026-11-14",
      "items": [
        { "match": { "id": "...", "homeTeam": {...}, "awayTeam": {...}, "kickoffAt": "...", "status": "SCHEDULED" },
          "cheeredTeamId": "...",
          "community": { "id": "...", "memberCount": 3, "joined": false },
          "enterOpensAt": "2026-11-14T17:00:00+09:00",
          "canEnter": false } ] },
    { "date": "2026-11-19", "items": [ ... ] }
  ]
}
```

- 응원 신청한 경기 중 **종료되지 않은 것만** 담는다(종료된 경기는 `/me/records`). `days`는 날짜 오름차순이고 같은 날 안에서는 킥오프 순이다. 날짜는 KST 기준으로 묶는다(`/matches?month=`와 같다).
- 신청 내역이 없으면 `days: []`, `count: 0`(200)이다. 프론트는 이때 "신청한 경기가 없어요"를 보여주고 캘린더로 보낸다.
- 프론트는 날짜별 목록을 보여주고, 입장 초대장을 하나씩 보여주며, `canEnter=false`인 초대장은 입장 버튼을 비활성화한다.
- (JSON 필드는 구현에서 snake_case다: `server_now`, `enter_opens_at`, `can_enter` 등)

**구현 메모 (§4.4)**

- 시각은 UTC(타임존 포함 ISO)로 내려간다. 위 예시의 `+09:00`은 표기용이고, 날짜별 묶음(`days[].date`)만 KST 기준이다.
- `GET /matches/{id}/community`와 `POST /communities/{id}/join`, `POST /communities/{id}/leave`는 갱신된 커뮤니티 정보 `{id, match_id, member_count, joined, enter_opens_at, can_enter}`를 돌려준다. 커뮤니티는 이 API를 처음 부를 때 만들어진다.
- `join` 거절은 `detail`이 객체다: `{"code": "NOT_CHEERED"}`(403), `{"code": "NOT_OPEN_YET", "enter_opens_at": ...}`(403), `{"code": "MATCH_FINISHED"}`(409). 검사 순서는 응원 신청 → 종료 → 입장 시간이다. 존재하지 않는 커뮤니티는 404.
- `leave`는 멤버가 아니어도 성공한다. 나가도 응원 기록은 그대로이고 입장 시간 안이면 다시 들어올 수 있다.
- `GET /communities/{id}/members`는 로그인한 누구나 볼 수 있고 `{data, count}`를 입장 순으로 돌려준다. 항목은 `user_id`, `nickname`, `profile_image_url`, `level`, `fairy_type`, `fairy_label`, `joined_at`이다(요정은 §3.2 규칙).
- 대결(§4.6)을 시작하거나 측정값을 보낼 때 커뮤니티 멤버인지는 검사하지 않는다.

### 4.5 랭킹 (폴링)

| Method | Path | 설명 |
| --- | --- | --- |
| GET | /rankings/victory?date=YYYY-MM-DD | 오늘의 승리요정 랭킹 (승률 desc) |
| GET | /rankings/defeat?date=YYYY-MM-DD | 오늘의 패배요정 랭킹 (패배율 desc) |

- `rankingPublic=false` 유저는 랭킹에서 제외.
- 프론트는 2~3초 폴링으로 "실시간" 느낌 연출.

**구현 메모 (BE-2)**

- 로그인 없이 볼 수 있다. 쿼리는 `date`(KST, 생략하면 오늘)와 `limit`(기본 20, 최대 100)이다.
- 후보는 `date`(KST) 하루에 킥오프한 경기에 **확정된 응원 기록**(PENDING 제외)이 있는 유저다. 승률·패배율·요정 판정은 그 날짜 끝까지의 **누적** 확정 기록으로 센다(`/me`와 같은 기준이라 오늘 날짜면 마이페이지의 요정과 항상 같다). `played`·`win`·`draw`·`lose`도 누적 값이다.
- 승률·패배율·요정 판정은 §3.1·§3.2의 `services/stats.py` 함수를 그대로 쓴다. 승리요정 랭킹에는 승리요정만, 패배요정 랭킹에는 패배요정만 오른다(둘 다 해당하면 승리요정 우선이라 패배요정 랭킹에는 없다). 중립요정은 어느 쪽에도 없다.
- 정렬은 비율(승률 또는 패배율) 내림차순 → 경기 수 내림차순 → `user_id`다. 순위는 1부터 매기고 동률도 번호가 겹치지 않는다.
- `ranking_public=false`인 유저는 뺀다(설정 행이 없으면 공개로 본다).
- 응답: `{date, kind: "VICTORY"|"DEFEAT", data: [{rank, user_id, nickname, fairy_label, profile_image_url, rate, played, win, draw, lose}], count}`. `rate`는 소수 둘째 자리까지다.

### 4.6 데시벨 대결 (소켓 없이 폴링)

| Method | Path | 설명 |
| --- | --- | --- |
| POST | /communities/{id}/battles | 대결 생성·시작. status=ONGOING, endsAt 세팅 |
| GET | /battles/{id} | 대결 상태 폴링: status, 남은시간, 현재 리더보드, 내 순위 |
| POST | /battles/{id}/records | 측정값 제출 `{peakDb}`. 기존보다 크면 갱신(max) |
| GET | /battles/{id}/result | 종료 후 TOP3 + 내 기록 + 내 상위 % |

**GET /battles/{id} 응답 예시 (폴링 대상)**

```json
{
  "id": 10,
  "status": "ONGOING",
  "remainingSec": 42,
  "leaderboard": [
    { "rank": 1, "nickname": "승리요정민지", "peakDb": 112.3 },
    { "rank": 2, "nickname": "아쉬운토끼",   "peakDb": 108.7 }
  ],
  "me": { "rank": 2, "peakDb": 92.7 }
}
```

**종료/정산 규칙**

- `endsAt` 지난 뒤 첫 `GET /battles/{id}` or `/result` 호출 시 서버가 status=FINISHED 전환(지연 정산). 별도 스케줄러 불필요.
- 종료 시 peakDb 상위 3명에게 포인트(100/50/30) 지급 + PointTransaction 기록.
- `maxPlayers`(5) 초과 입장 불가.
- 구현 메모: `POST /communities/{id}/battles` 본문 `{duration_sec}`(선택, 기본 60). 진행 중 대결이 있으면 새로 만들지 않고 그 대결을 돌려준다(모두 같은 대결 참여). `POST /battles/{id}/records`는 갱신된 대결 상태(GET과 같은 형태)를 돌려주므로 프론트는 측정 중 1초마다 제출하고 응답 리더보드를 그대로 쓴다. `/result`는 `{top3, me, my_top_percent, participants, my_points}`, 종료 전이면 409. `top3[]` 각 항목에는 실제로 받은 포인트 `points`가 들어 있고(PointTransaction에서 읽는다), `my_points`는 내가 받은 포인트다(TOP3 밖이면 0). `GET /communities/today`는 오늘(KST) 가장 이른 경기의 커뮤니티를 없으면 만들어 돌려준다.
- 구현 메모 (정산): `endsAt`이 지난 뒤 처음 오는 `GET /battles/{id}`, `/result`, `POST /battles/{id}/records` 중 하나가 정산한다. 대결 행을 잠그고(`FOR UPDATE`) 다시 읽어 ONGOING을 본 요청 하나만 정산하므로 동시에 폴링해도 두 번 지급되지 않는다. peakDb 상위 3명에게 100/50/30을 `services/settlement.py`의 `grant_points(reason=DECIBEL_TOP3, related_id=battleId)`로 지급하고(3명 미만이면 있는 사람만), 참가자 전원을 `evaluate_badges(peak_db=)`로 데시벨 마스터 평가한다. 상태 전환·지급·배지는 한 트랜잭션이다. 기록 제출은 같은 행을 공유 잠금(`FOR SHARE`)으로 다시 읽고 `endsAt` 전인지 확인하므로, 정산과 겹치면 정산 쪽이 그 제출의 커밋을 기다려 순위에 반영하거나 제출이 409가 된다(정산 뒤에 기록이 끼어들지 않는다).

### 4.7 운세 (시드 → AI)

| Method | Path | 설명 |
| --- | --- | --- |
| GET | /matches/{id}/fortune?team_id= | 경기 당일 응원팀 운세. 두 팀 선수의 생년월일로 계산한 등급·선수 하이라이트를 시드 문구 풀에서 즉시 반환 |

**응답 예시**

```json
{
  "matchId": 100, "teamId": 3,
  "fortuneText": "흐름이 좋은 날이에요! 초반에 선취점을 뽑으면 승리 확률이 높아요",
  "cheerTip": "7회 이후 불펜 운용을 주목하세요",
  "luckScore": 78,
  "grade": "중길",
  "luckyPlayers": [
    {"kboId": 55208, "name": "홍길동", "position": "포수", "backNumber": "27",
     "birthYear": 1998, "grade": "대길", "luckScore": 94, "oneLiner": "홍길동 선수, 오늘은 배트에 눈이 달렸어요"}
  ],
  "cautionPlayer": {"kboId": 60112, "name": "김철수", "position": "투수", "backNumber": "41",
     "birthYear": 2001, "grade": "대흉", "luckScore": 3, "oneLiner": "김철수 선수, 오늘은 공이 좀 안 보이는 날"}
}
```

(JSON 키는 실제로는 snake_case — `lucky_players`, `caution_player`, `birth_year` 등. 위는 명세 표기 관례.)

**계산 규칙** (정본. 코드는 `app/ai/fortune_players.py`)

- 후보 선수 = 응원팀 `Player` 중 등번호가 0~99인 사람(팀당 60~72명). 등번호 3자리(육성)·없음은 제외한다. 1군·라인업 구분 데이터가 없어서 팬이 모를 2군 이름을 줄이는 근사치다.
- 선수 점수 = `sha256("생년월일:경기일(KST)") % 100`. 같은 날 같은 생일이면 같은 점수, 정렬 동점은 `kboId` 오름차순.
- 등급(선수·팀 공통): 88↑ 대길 · 68↑ 중길 · 43↑ 소길 · 23↑ 소흉 · 8↑ 중흉 · 그 아래 대흉 (길 57% / 흉 43%).
- 팀 점수 = 후보 평균을 정규분포 누적확률로 변환한 퍼센타일 `round(100 × Φ((평균−49.5) / (28.87/√n)))`. 단순 평균은 ~50에 몰리고 상위 N명 평균은 항상 대길이라 이렇게 한다. `luck_score`가 이 값이다.
- `lucky_players` = 점수 상위 3명(기운 좋은 선수), `caution_player` = 최하위 1명(그 등급이 흉 계열일 때만, 아니면 null). 팀 등급과 선수 등급은 독립이다.
- 후보가 4명 미만이면 기존 팀 시드(`fortune_seed.json`)로 폴백하고 `lucky_players=[]`, `caution_player=null`.
- 문구는 `app/ai/fortune_grades.json`의 등급 풀에서 `sha256(날짜:팀id:등급)`으로 고른다. 같은 날 같은 팀은 항상 같은 결과, 두 팀이 같은 등급이면 문구가 다르다. 네트워크·DB 저장 없음.
- 가짜 라인업은 만들지 않는다. 후보가 실제 출전한다는 보장이 없으므로 문구는 "오늘 기운 좋은 선수"로 쓴다.

**화면·톤 방침 (FE·문구 작성 기준)**

- 위계: 팀 등급(큰 글씨) → 기운 좋은 선수 3명 + 조심할 선수 1명. 전체 명단은 보여주지 않는다. 두 팀을 나란히 보여 대비를 만들고 내 응원팀을 위에 둔다.
- 생년월일은 `birth_year`만 내린다("98년생"). 코치·감독은 쓰지 않는다.
- 화면 구석에 "재미로 보는 운세"를 표기한다.
- 흉 문구는 가볍게(선수를 깎아내리지 않는다. 부상·사생활·승부 단정 금지). 팀 흉 문구·팁의 끝은 "응원으로 뒤집자"로 맺어 데시벨 대결로 잇는다.
- 선수별 생일 보너스는 후속(여유 시).
- 세부 계획·결정 근거: `docs/fortune-players-plan.md`.

- **후속(AI)**: 프롬프트 = 팀명 + 상대팀 + 최근 폼(옵션). 조회 순서는 `Fortune` 캐시(matchId, teamId, date 유니크) → AI → 시드 풀. AI 결과만 `Fortune`에 저장하고, 실패하면 시드로 내려간다. 호출 코드는 `app/ai/fortune.py`에 보관돼 있다. 등급·선수 하이라이트는 코드가 계산하고 AI는 문구만 바꾸는 구조로 간다.
- (양념) 응원 기록 기반 AI 한 줄 평도 같은 패턴으로 추가 가능.

## 5. 화면 ↔ API 매핑 (목업 기준)

| 화면 | 사용 API |
| --- | --- |
| 캘린더 | GET /matches?month |
| 팀 응원 설정 | GET /matches/{id}, POST /matches/{id}/cheer |
| 초대장 → 커뮤니티 입장 | GET /matches/{id}/community, POST /communities/{id}/join |
| 커뮤니티 홈 (내 경기 목록·초대장) | GET /communities/mine |
| 커뮤니티 홈 (랭킹) | GET /communities/today, /rankings/victory, /rankings/defeat |
| 데시벨 측정/대결방 | POST /communities/{id}/battles, GET /battles/{id} (폴링), POST /battles/{id}/records |
| 대결 종료/보상 | GET /battles/{id}/result |
| 마이페이지 | GET /me, /me/records, /me/stats, /me/badges, /me/points |
| SNS 공유 카드 | GET /me/share-card |
| 당일 운세 | GET /matches/{id}/fortune?teamId |
| 설정 | GET/PATCH /me/settings, /me/profile, /me/teams |

## 6. 개발 우선순위 & 팀 분담 (백2·프1·AI1 / 남은 시간 기준)

**코어 (반드시)**
- BE-1: User/Team/Match/CheerRecord + 인증 스텁 + 경기 일정/캘린더 API + 시드 데이터 + 경기 종료 정산(포인트·요정·배지)
- BE-2: Community/Battle/BattleRecord + 데시벨 대결 폴링 API + 랭킹 API + 포인트/배지 조회
- FE: 캘린더 → 응원설정 → 커뮤니티 → 데시벨 측정(Web Audio API) → 마이페이지 순으로 핵심 플로우
- AI: 운세 시드 문구 풀 + API(AI 생성은 후속), (여유 시) 기록 AI 한 줄 평

**양념 (되면)**
- 운세 화면, SNS 공유 카드 이미지, 배지 연출

**스트레치 (최후)**
- 외부 경기 API 실연동, 커뮤니티 메시지 피드(REST 폴링), 레벨/성향 그래프 고도화

## 7. 데모 시나리오 (심사용 3분)

1. 캘린더에서 오늘 경기(두산 vs LG) 선택 → LG 응원 설정
2. 초대장 → 커뮤니티 입장 → 데시벨 대결 시작, 다 같이 소리 질러 측정 (입장은 경기 시작 1시간 전부터라, 시연 경기는 킥오프가 1시간 이내여야 한다)
3. TOP3 + 포인트 지급 화면
4. `admin/finish`로 경기 종료 발동 → 승리 결과·포인트·요정 갱신
5. 마이페이지에서 승률·요정·배지 확인 → SNS 공유 카드로 마무리
