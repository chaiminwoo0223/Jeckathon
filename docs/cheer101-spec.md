# CHEER 101 — 기능 명세서

> 스포츠 경기 관람 기록 + 응원 커뮤니티 + 데시벨 대결 서비스. 해커톤 산출물 기준으로 백엔드가 바로 개발에 착수할 수 있도록 **데이터 모델 / API / 비즈니스 규칙** 중심으로 정리.

## 0. 핵심 아키텍처 결정

- **채팅 외 실시간 미사용.** 데시벨 대결·랭킹 등 채팅을 뺀 전부는 **REST + 폴링(2~3초 간격)** 과 DB 조회로 처리한다. 채팅은 범위에 남기고, 폴링으로 부족하면 그때만 WebSocket을 붙인다(별도 소켓 서버 없이 같은 FastAPI 앱 안에서).
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
| 운세(Fortune) | 경기 당일 응원팀 기준 AI 생성 운세 |

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

### 2.11 Fortune (운세, AI 생성 캐시)

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

**경기 종료 처리 (내부 배치/관리자 트리거)**

- `PATCH /admin/matches/{id}/finish` `{homeScore, awayScore}` 호출 시:
  1. Match status=FINISHED, 스코어 저장
  2. 해당 경기의 PENDING CheerRecord 전부 result 확정 (응원팀 기준 승/무/패)
  3. 결과별 포인트 지급 + PointTransaction 기록
  4. 유저별 승률/요정/배지 재평가
- 데모에서는 이 엔드포인트로 "경기 끝남"을 수동 발동해 결과 화면을 시연.

### 4.4 커뮤니티

| Method | Path | 설명 |
| --- | --- | --- |
| GET | /communities/today | 오늘의 커뮤니티 (대표 경기 1개 + 메타) |
| GET | /matches/{id}/community | 경기별 커뮤니티 정보 (멤버 수, 내 입장 여부) |
| POST | /communities/{id}/join | 입장 (초대장 → 입장) |
| POST | /communities/{id}/leave | 나가기 |
| GET | /communities/{id}/members | 멤버 목록 (프로필, 요정 타입) |

### 4.5 랭킹 (폴링)

| Method | Path | 설명 |
| --- | --- | --- |
| GET | /rankings/victory?date=YYYY-MM-DD | 오늘의 승리요정 랭킹 (승률 desc) |
| GET | /rankings/defeat?date=YYYY-MM-DD | 오늘의 패배요정 랭킹 (패배율 desc) |

- `rankingPublic=false` 유저는 랭킹에서 제외.
- 프론트는 2~3초 폴링으로 "실시간" 느낌 연출.

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

### 4.7 운세 (AI)

| Method | Path | 설명 |
| --- | --- | --- |
| GET | /matches/{id}/fortune?teamId= | 경기 당일 운세. 캐시 없으면 AI 생성 후 저장·반환 |

**응답 예시**

```json
{
  "matchId": 100, "teamId": 3,
  "fortuneText": "흐름이 좋은 날이에요! 초반에 선취점을 뽑으면 승리 확률이 높아요",
  "cheerTip": "7회 이후 불펜 운용을 주목하세요",
  "luckScore": 78
}
```

- **AI 담당**: 프롬프트 = 팀명 + 상대팀 + 최근 폼(옵션). 톤은 "쓸모없지만 그럴듯한" 운세. 결과를 `Fortune` 테이블에 (matchId, teamId, date) 유니크로 캐싱해 중복 호출 방지.
- (양념) 응원 기록 기반 AI 한 줄 평도 같은 패턴으로 추가 가능.

## 5. 화면 ↔ API 매핑 (목업 기준)

| 화면 | 사용 API |
| --- | --- |
| 캘린더 | GET /matches?month |
| 팀 응원 설정 | GET /matches/{id}, POST /matches/{id}/cheer |
| 초대장 → 커뮤니티 입장 | GET /matches/{id}/community, POST /communities/{id}/join |
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
- AI: 운세 생성 API + 프롬프트 튜닝, (여유 시) 기록 AI 한 줄 평

**양념 (되면)**
- 운세 화면, SNS 공유 카드 이미지, 배지 연출

**스트레치 (최후)**
- 외부 경기 API 실연동, 커뮤니티 메시지 피드(REST 폴링), 레벨/성향 그래프 고도화

## 7. 데모 시나리오 (심사용 3분)

1. 캘린더에서 오늘 경기(두산 vs LG) 선택 → LG 응원 설정
2. 초대장 → 커뮤니티 입장 → 데시벨 대결 시작, 다 같이 소리 질러 측정
3. TOP3 + 포인트 지급 화면
4. `admin/finish`로 경기 종료 발동 → 승리 결과·포인트·요정 갱신
5. 마이페이지에서 승률·요정·배지 확인 → SNS 공유 카드로 마무리
