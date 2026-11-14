# 응원 스타디움 (Arena Metaverse) — 설계

커뮤니티 안에서 3D 경기장을 돌아다니며 다른 팬 아바타와 함께 응원하는 메타버스 공간. 1단계는 FE 단독(연출 봇), 2단계는 백엔드 WebSocket 실시간 동기화.

## 범위

- **소유 영역**: `frontend/` 전부 (FE 담당). 백엔드 변경 없음.
- **1단계 (이번 작업)**: 진짜 3D 렌더링 + 연출용 봇 아바타. FE만으로 완결.
- **2단계 (백엔드 준비 후)**: `presence` 구현체만 WebSocket으로 교체. 씬 코드 변경 없음.

## 진입 흐름

커뮤니티 페이지(`frontend/src/routes/cheer/community.tsx`)의 기존 스테이지 머신(`invite → room → measuring → result`)에 `arena` 스테이지를 추가한다.

- `Room` 안에 **"🏟️ 응원 스타디움 입장"** 버튼 → `stage = "arena"`.
- Arena 뷰 우상단 **나가기** 버튼 → `stage = "room"`.
- 기존 스테이지 동작은 변경하지 않는다.

## 3D 씬 (self-contained)

저장소가 PUBLIC이고 데모 안정성이 중요하므로 **외부 GLB/텍스처를 쓰지 않고 코드 생성 로우폴리**로 구성한다 (three primitive geometry). CSP·에셋 로딩 리스크 없음.

- **경기장**: 초록 잔디 바닥 + 흰 필드 라인, 둘러싼 관중석 단, 하늘/안개, 중앙에 대형 중계 스크린(placeholder).
- **아바타**: 둥근 캐릭터(캡슐 몸통 + 구 머리). 머리 위에 **닉네임 라벨 + 말풍선**.
- **유니폼**: 각 아바타는 **응원 팀 유니폼**을 입는다. 유니폼 색 = 팀 컬러, 가슴/등에 **팀명 텍스트 라벨**(카메라를 향하는 billboard text). 봇은 `src/cheer/data/mock.ts`의 `TEAMS`에서 랜덤 배정, 나는 내 응원 팀.

## 조작 & 카메라

- 이동: **WASD / 방향키**, 모바일은 화면 **가상 조이스틱(드래그)**.
- 카메라: 내 아바타 3인칭 추적 + 마우스/터치 드래그로 약간 회전.
- 바닥 경계 clamp(경기장 밖으로 못 나감). 충돌 물리는 없음.

## Presence 추상화 (교체 대비 핵심)

씬은 `players: Player[]`만 그린다. presence 소스를 hook 뒤로 숨겨 1→2단계 전환 시 씬 코드 변경이 없게 한다.

```ts
type Player = {
  id: string
  nickname: string
  team: { name: string; color: string }
  position: { x: number; z: number }
  rotation: number      // 바라보는 방향(rad)
  message?: string      // 말풍선(있으면 표시)
  isMe: boolean
}

usePresence(): {
  players: Player[]
  me: Player
  move(next: { x: number; z: number; rotation: number }): void
}
```

- **1단계**: `createMockPresence()` — 봇 6~8명이 랜덤 배회(waypoint 보간) + 가끔 말풍선(`COMMUNITY_FEED`/응원 문구 재사용).
- **2단계**: `createSocketPresence(ws)` — 동일 인터페이스, FastAPI `@router.websocket` 연동. (BE-2 협의 필요, 명세 §0 "채팅 외 실시간은 폴링" 원칙의 예외로 WS 추가.)

## 파일 구성 (전부 `frontend/`)

```
src/cheer/arena/
  arena-stage.tsx          # <Canvas> + HUD + 나가기 버튼
  scene/
    stadium.tsx            # 잔디·라인·관중석·스크린·조명·하늘
    avatar.tsx             # 캐릭터 + 유니폼 + 팀명 라벨
    speech-bubble.tsx      # 머리 위 말풍선/닉네임
  controls/
    use-movement.ts        # 키보드 입력 → 내 위치 업데이트
    joystick.tsx           # 모바일 가상 조이스틱
  presence/
    types.ts               # Player 타입
    use-presence.ts        # 공개 hook (현재 mock 구현을 반환)
    mock-presence.ts       # 봇 배회 로직
```

`community.tsx`에는 입장 버튼 + `arena` 스테이지 분기만 추가(최소 변경).

## 의존성

`three`, `@react-three/fiber`, `@react-three/drei` 추가. bun으로 설치. (`bun run lint` 통과 기준.)

## 완료 기준

1. 커뮤니티 Room에서 "응원 스타디움 입장" → 3D 경기장이 뜬다.
2. WASD/방향키(데스크톱)·조이스틱(모바일)으로 내 아바타가 경기장을 돌아다닌다.
3. 봇 아바타 여러 명이 배회하고 가끔 말풍선을 띄운다.
4. 모든 아바타가 **팀명이 박힌 유니폼**을 입고 있다.
5. 나가기로 커뮤니티로 복귀한다.
6. `bun run lint` 통과.

## 범위 밖 (YAGNI, 2단계로 이월)

실시간 WebSocket 동기화, 음성, 충돌 물리, 다운로드 3D 모델, 위치 영속화.
