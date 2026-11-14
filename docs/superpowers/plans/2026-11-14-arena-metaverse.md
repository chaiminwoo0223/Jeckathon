# 응원 스타디움 (Arena Metaverse) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 커뮤니티 안에 3D 경기장을 추가해 팬 아바타(팀 유니폼 착용)로 돌아다니며 응원하는 메타버스 공간을 만든다.

**Architecture:** React Three Fiber(`<Canvas>`)로 코드 생성 로우폴리 경기장을 렌더. 접속자는 `usePresence` hook 뒤로 추상화하고 1단계는 mock 봇, 2단계는 WebSocket으로 구현체만 교체. 커뮤니티 페이지의 기존 stage 머신에 `arena` 스테이지를 더한다.

**Tech Stack:** React, TypeScript, Vite, TanStack Router, Tailwind, three, @react-three/fiber, @react-three/drei, bun.

**검증 방식:** 프론트 테스트 러너 없음 → 각 태스크는 `bun run lint` 통과 + `bun run dev` 시각 확인으로 검증. 순수 로직(경계 clamp, 봇 wander)은 작은 순수 함수로 분리해 콘솔/시각으로 확인.

---

## File Structure

```
frontend/src/cheer/arena/
  arena-stage.tsx          # <Canvas> + HUD(나가기) 진입점
  scene/
    stadium.tsx            # 잔디·필드라인·관중석·중계스크린·조명·하늘
    avatar.tsx             # 캐릭터 메시 + 유니폼 + 팀명 라벨 + 말풍선 연결
    speech-bubble.tsx      # 머리 위 닉네임 라벨 + 말풍선(Html/Billboard)
  controls/
    use-movement.ts        # 키보드 입력 → 내 위치/회전, 경계 clamp
    joystick.tsx           # 모바일 가상 조이스틱(터치 드래그)
  presence/
    types.ts               # Player 타입, 상수(경기장 반경 등)
    mock-presence.ts       # 봇 생성 + wander step(순수 로직)
    use-presence.ts        # 공개 hook (현재 mock 구현 반환)
```

수정: `frontend/src/routes/cheer/community.tsx` (입장 버튼 + `arena` 분기), `frontend/package.json` (deps).

---

## Task 1: 의존성 추가

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: three + R3F 설치**

Run:
```bash
cd frontend && bun add three @react-three/fiber @react-three/drei && bun add -d @types/three
```
Expected: package.json에 `three`, `@react-three/fiber`, `@react-three/drei`, `@types/three` 추가, 설치 성공.

- [ ] **Step 2: 설치 확인**

Run: `cd frontend && grep -E "three|fiber|drei" package.json`
Expected: 4개 항목 출력.

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/bun.lock
git commit -m "chore(fe): three/@react-three 의존성 추가"
```

---

## Task 2: Presence 타입 + 상수

**Files:**
- Create: `frontend/src/cheer/arena/presence/types.ts`

- [ ] **Step 1: 타입/상수 작성**

```ts
// frontend/src/cheer/arena/presence/types.ts
export type ArenaTeam = { name: string; color: string }

export type Player = {
  id: string
  nickname: string
  team: ArenaTeam
  x: number
  z: number
  rotation: number // 바라보는 방향(rad)
  message?: string // 있으면 말풍선 표시
  isMe: boolean
}

export type PresenceApi = {
  players: Player[]
  me: Player
  move: (next: { x: number; z: number; rotation: number }) => void
}

// 경기장(원형 잔디) 반경. 아바타는 이 안에서만 이동.
export const ARENA_RADIUS = 18
// 아바타가 경계에 닿지 않도록 여유
export const ARENA_PLAY_RADIUS = ARENA_RADIUS - 1.5
```

- [ ] **Step 2: Lint**

Run: `cd frontend && bun run lint`
Expected: 통과(신규 파일 에러 없음).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/cheer/arena/presence/types.ts
git commit -m "feat(fe): arena presence 타입/상수 추가"
```

---

## Task 3: Mock presence (봇 생성 + wander 순수 로직)

**Files:**
- Create: `frontend/src/cheer/arena/presence/mock-presence.ts`

데이터 소스: `frontend/src/cheer/data/mock.ts`의 `TEAMS`(팀명/컬러), `COMMUNITY_FEED`(말풍선 문구). 실제 export 이름은 구현 전 `grep -n "export" src/cheer/data/mock.ts`로 확인하고 맞춘다.

- [ ] **Step 1: 봇 생성 + step 함수 작성**

```ts
// frontend/src/cheer/arena/presence/mock-presence.ts
import { ARENA_PLAY_RADIUS, type ArenaTeam, type Player } from "./types"

const CHEERS = ["가자!!", "이겨라 🔥", "와아아아", "골!! ⚽", "오늘 이긴다", "파이팅!", "💪💪", "최고야"]

type Bot = Player & {
  targetX: number
  targetZ: number
  speed: number
  nextTalkAt: number // ms 타임스탬프
}

function randomPointInArena(rand: () => number) {
  const r = Math.sqrt(rand()) * ARENA_PLAY_RADIUS
  const a = rand() * Math.PI * 2
  return { x: Math.cos(a) * r, z: Math.sin(a) * r }
}

// teams: {name,color}[] (mock TEAMS에서 매핑), names: 봇 닉네임 후보
export function createBots(
  teams: ArenaTeam[],
  names: string[],
  now: number,
  rand: () => number = Math.random,
): Bot[] {
  return names.map((nickname, i) => {
    const p = randomPointInArena(rand)
    const t = randomPointInArena(rand)
    return {
      id: `bot-${i}`,
      nickname,
      team: teams[i % teams.length],
      x: p.x,
      z: p.z,
      rotation: rand() * Math.PI * 2,
      isMe: false,
      targetX: t.x,
      targetZ: t.z,
      speed: 1.6 + rand() * 1.0,
      nextTalkAt: now + 2000 + rand() * 6000,
    }
  })
}

// dt: 초 단위 경과. 봇을 target 쪽으로 이동, 도착하면 새 target, 때때로 말풍선.
export function stepBots(bots: Bot[], dt: number, now: number, rand: () => number = Math.random): Bot[] {
  return bots.map((b) => {
    const dx = b.targetX - b.x
    const dz = b.targetZ - b.z
    const dist = Math.hypot(dx, dz)
    let { x, z, rotation, targetX, targetZ, message, nextTalkAt } = b
    if (dist < 0.3) {
      const t = randomPointInArena(rand)
      targetX = t.x
      targetZ = t.z
    } else {
      const move = Math.min(dist, b.speed * dt)
      x += (dx / dist) * move
      z += (dz / dist) * move
      rotation = Math.atan2(dx, dz)
    }
    if (now >= nextTalkAt) {
      message = CHEERS[Math.floor(rand() * CHEERS.length)]
      nextTalkAt = now + 4000 + rand() * 8000
    } else if (message && now >= nextTalkAt - 6000) {
      // 말풍선 노출 후 일정 시간 지나면 제거(대략)
      message = now >= nextTalkAt - 2500 ? message : message
    }
    return { ...b, x, z, rotation, targetX, targetZ, message, nextTalkAt }
  })
}
```

주: 말풍선 노출/소거 타이밍은 Task 7 hook에서 명시적으로 관리하므로, 여기서는 단순히 `message`를 세팅/유지한다. 위 else 분기는 no-op에 가깝다 — hook에서 정리한다(아래 Task 7에서 message TTL 관리).

- [ ] **Step 2: Lint**

Run: `cd frontend && bun run lint`
Expected: 통과. (미사용 변수 경고 나오면 제거.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/cheer/arena/presence/mock-presence.ts
git commit -m "feat(fe): arena 봇 wander 로직(mock presence)"
```

---

## Task 4: usePresence hook

**Files:**
- Create: `frontend/src/cheer/arena/presence/use-presence.ts`

- [ ] **Step 1: hook 작성 (내 아바타 + 봇 루프 + 말풍선 TTL)**

```ts
// frontend/src/cheer/arena/presence/use-presence.ts
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { TEAMS } from "@/cheer/data/mock"
import { createBots, stepBots } from "./mock-presence"
import { type ArenaTeam, type Player, type PresenceApi } from "./types"

const BOT_NAMES = ["열혈팬준호", "응원요정지수", "함성대장", "골세레머니", "치어리더민", "북치는곰", "붉은악마", "승리기원"]

// mock.ts의 TEAMS를 {name,color}[]로 매핑. (실제 TEAMS 구조에 맞게 조정)
function arenaTeams(): ArenaTeam[] {
  return Object.values(TEAMS).map((t: any) => ({ name: t.name, color: t.color ?? "#e11d48" }))
}

export function usePresence(myNickname: string, myTeam: ArenaTeam): PresenceApi {
  const teams = useMemo(arenaTeams, [])
  const meRef = useRef<Player>({
    id: "me",
    nickname: myNickname,
    team: myTeam,
    x: 0,
    z: 6,
    rotation: Math.PI,
    isMe: true,
  })
  const botsRef = useRef(createBots(teams, BOT_NAMES.slice(0, 7), performance.now()))
  const talkClearRef = useRef<Record<string, number>>({})
  const [players, setPlayers] = useState<Player[]>([meRef.current, ...botsRef.current])

  const move = useCallback((next: { x: number; z: number; rotation: number }) => {
    meRef.current = { ...meRef.current, ...next }
  }, [])

  useEffect(() => {
    let raf = 0
    let last = performance.now()
    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000)
      last = now
      const stepped = stepBots(botsRef.current, dt, now)
      // 말풍선 TTL: 새로 생긴 메시지는 3.5초 뒤 제거
      for (const b of stepped) {
        if (b.message && talkClearRef.current[b.id] == null) talkClearRef.current[b.id] = now + 3500
      }
      botsRef.current = stepped.map((b) => {
        const clearAt = talkClearRef.current[b.id]
        if (clearAt != null && now >= clearAt) {
          delete talkClearRef.current[b.id]
          return { ...b, message: undefined }
        }
        return b
      })
      setPlayers([meRef.current, ...botsRef.current])
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [])

  return { players, me: meRef.current, move }
}
```

- [ ] **Step 2: Lint**

Run: `cd frontend && bun run lint`
Expected: 통과. `any` 경고 시 TEAMS 실제 타입으로 교체.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/cheer/arena/presence/use-presence.ts
git commit -m "feat(fe): usePresence hook(봇 루프+말풍선 TTL)"
```

---

## Task 5: 경기장 씬 (stadium)

**Files:**
- Create: `frontend/src/cheer/arena/scene/stadium.tsx`

- [ ] **Step 1: 경기장 메시 작성**

```tsx
// frontend/src/cheer/arena/scene/stadium.tsx
import { ARENA_RADIUS } from "../presence/types"

export function Stadium() {
  return (
    <group>
      {/* 하늘/환경광 */}
      <ambientLight intensity={0.8} />
      <directionalLight position={[10, 20, 10]} intensity={1.1} castShadow />
      <hemisphereLight args={["#cfe8ff", "#3a5f2a", 0.5]} />

      {/* 잔디 원형 바닥 */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[ARENA_RADIUS, 64]} />
        <meshStandardMaterial color="#3f8f3a" />
      </mesh>

      {/* 중앙 서클 라인 */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <ringGeometry args={[2.4, 2.6, 48]} />
        <meshStandardMaterial color="#eafff0" />
      </mesh>

      {/* 관중석(둘러싼 링, 살짝 높임) */}
      <mesh position={[0, 0.6, 0]}>
        <cylinderGeometry args={[ARENA_RADIUS + 3, ARENA_RADIUS + 1.5, 2, 64, 1, true]} />
        <meshStandardMaterial color="#d7dbe6" side={2} />
      </mesh>

      {/* 중계 스크린 */}
      <group position={[0, 5, -(ARENA_RADIUS + 1)]}>
        <mesh>
          <boxGeometry args={[10, 5, 0.4]} />
          <meshStandardMaterial color="#111827" emissive="#1e293b" emissiveIntensity={0.4} />
        </mesh>
      </group>
    </group>
  )
}
```

- [ ] **Step 2: Lint**

Run: `cd frontend && bun run lint`
Expected: 통과.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/cheer/arena/scene/stadium.tsx
git commit -m "feat(fe): arena 경기장 씬"
```

---

## Task 6: 아바타 + 말풍선

**Files:**
- Create: `frontend/src/cheer/arena/scene/speech-bubble.tsx`
- Create: `frontend/src/cheer/arena/scene/avatar.tsx`

- [ ] **Step 1: speech-bubble (닉네임 라벨 + 말풍선)**

```tsx
// frontend/src/cheer/arena/scene/speech-bubble.tsx
import { Html } from "@react-three/drei"

export function NameTag({ nickname, message }: { nickname: string; message?: string }) {
  return (
    <Html position={[0, 2.4, 0]} center distanceFactor={14} zIndexRange={[10, 0]} pointerEvents="none">
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4, pointerEvents: "none" }}>
        {message && (
          <div style={{ background: "#fff", color: "#111827", borderRadius: 14, padding: "4px 10px", fontSize: 13, fontWeight: 700, boxShadow: "0 4px 12px rgba(0,0,0,.18)", whiteSpace: "nowrap" }}>
            {message}
          </div>
        )}
        <div style={{ background: "rgba(17,24,39,.78)", color: "#fff", borderRadius: 10, padding: "2px 8px", fontSize: 11, fontWeight: 700, whiteSpace: "nowrap" }}>
          {nickname}
        </div>
      </div>
    </Html>
  )
}
```

- [ ] **Step 2: avatar (유니폼 색 + 팀명 라벨 + 몸/머리)**

```tsx
// frontend/src/cheer/arena/scene/avatar.tsx
import { Billboard, Text } from "@react-three/drei"
import { type Player } from "../presence/types"
import { NameTag } from "./speech-bubble"

export function Avatar({ player }: { player: Player }) {
  const { x, z, rotation, team, isMe } = player
  return (
    <group position={[x, 0, z]} rotation={[0, rotation, 0]}>
      {/* 몸통(유니폼) */}
      <mesh position={[0, 0.7, 0]} castShadow>
        <capsuleGeometry args={[0.45, 0.7, 6, 12]} />
        <meshStandardMaterial color={team.color} />
      </mesh>
      {/* 머리 */}
      <mesh position={[0, 1.55, 0]} castShadow>
        <sphereGeometry args={[0.38, 16, 16]} />
        <meshStandardMaterial color="#ffdcb5" />
      </mesh>
      {/* 가슴 팀명 라벨(카메라 향함) */}
      <Billboard position={[0, 0.9, 0]}>
        <Text fontSize={0.22} color="#ffffff" anchorX="center" anchorY="middle" maxWidth={1} outlineWidth={0.01} outlineColor="#00000055">
          {team.name}
        </Text>
      </Billboard>
      {/* 내 아바타 발밑 하이라이트 */}
      {isMe && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
          <ringGeometry args={[0.55, 0.7, 24]} />
          <meshStandardMaterial color="#f6b93b" />
        </mesh>
      )}
      <NameTag nickname={player.nickname} message={player.message} />
    </group>
  )
}
```

- [ ] **Step 3: Lint**

Run: `cd frontend && bun run lint`
Expected: 통과.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/cheer/arena/scene/speech-bubble.tsx frontend/src/cheer/arena/scene/avatar.tsx
git commit -m "feat(fe): arena 아바타(팀 유니폼/팀명 라벨)+말풍선"
```

---

## Task 7: 이동 컨트롤 (키보드 + 경계 clamp)

**Files:**
- Create: `frontend/src/cheer/arena/controls/use-movement.ts`

- [ ] **Step 1: 경계 clamp 순수 함수 + 키보드 hook**

```ts
// frontend/src/cheer/arena/controls/use-movement.ts
import { useEffect, useRef } from "react"
import { ARENA_PLAY_RADIUS } from "../presence/types"

// 원형 경계 안으로 좌표 제한
export function clampToArena(x: number, z: number): { x: number; z: number } {
  const d = Math.hypot(x, z)
  if (d <= ARENA_PLAY_RADIUS) return { x, z }
  const s = ARENA_PLAY_RADIUS / d
  return { x: x * s, z: z * s }
}

export type MoveInput = { x: number; z: number } // 정규화된 방향(-1..1)

// 키보드 입력을 ref로 수집. (조이스틱도 같은 ref에 쓸 수 있게 반환)
export function useKeyboardInput() {
  const input = useRef<MoveInput>({ x: 0, z: 0 })
  useEffect(() => {
    const keys = new Set<string>()
    const recompute = () => {
      let x = 0
      let z = 0
      if (keys.has("KeyW") || keys.has("ArrowUp")) z -= 1
      if (keys.has("KeyS") || keys.has("ArrowDown")) z += 1
      if (keys.has("KeyA") || keys.has("ArrowLeft")) x -= 1
      if (keys.has("KeyD") || keys.has("ArrowRight")) x += 1
      const len = Math.hypot(x, z) || 1
      input.current = { x: x / len, z: z / len }
    }
    const down = (e: KeyboardEvent) => {
      keys.add(e.code)
      recompute()
    }
    const up = (e: KeyboardEvent) => {
      keys.delete(e.code)
      recompute()
    }
    window.addEventListener("keydown", down)
    window.addEventListener("keyup", up)
    return () => {
      window.removeEventListener("keydown", down)
      window.removeEventListener("keyup", up)
    }
  }, [])
  return input
}
```

- [ ] **Step 2: Lint**

Run: `cd frontend && bun run lint`
Expected: 통과.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/cheer/arena/controls/use-movement.ts
git commit -m "feat(fe): arena 이동 입력+경계 clamp"
```

---

## Task 8: 모바일 조이스틱

**Files:**
- Create: `frontend/src/cheer/arena/controls/joystick.tsx`

- [ ] **Step 1: 터치 조이스틱(입력 ref에 값 주입)**

```tsx
// frontend/src/cheer/arena/controls/joystick.tsx
import { useRef, useState } from "react"
import { type MoveInput } from "./use-movement"

const R = 52 // 베이스 반경(px)

export function Joystick({ inputRef }: { inputRef: React.MutableRefObject<MoveInput> }) {
  const base = useRef<HTMLDivElement>(null)
  const [knob, setKnob] = useState({ x: 0, y: 0 })
  const active = useRef(false)

  const set = (clientX: number, clientY: number) => {
    const el = base.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    let dx = clientX - cx
    let dy = clientY - cy
    const d = Math.hypot(dx, dy)
    if (d > R) {
      dx = (dx / d) * R
      dy = (dy / d) * R
    }
    setKnob({ x: dx, y: dy })
    inputRef.current = { x: dx / R, z: dy / R }
  }
  const reset = () => {
    active.current = false
    setKnob({ x: 0, y: 0 })
    inputRef.current = { x: 0, z: 0 }
  }

  return (
    <div
      ref={base}
      className="absolute bottom-6 left-6 size-[112px] touch-none rounded-full bg-black/20 backdrop-blur-sm md:hidden"
      onTouchStart={(e) => {
        active.current = true
        set(e.touches[0].clientX, e.touches[0].clientY)
      }}
      onTouchMove={(e) => active.current && set(e.touches[0].clientX, e.touches[0].clientY)}
      onTouchEnd={reset}
    >
      <div
        className="absolute left-1/2 top-1/2 size-12 rounded-full bg-white/80 shadow"
        style={{ transform: `translate(calc(-50% + ${knob.x}px), calc(-50% + ${knob.y}px))` }}
      />
    </div>
  )
}
```

- [ ] **Step 2: Lint**

Run: `cd frontend && bun run lint`
Expected: 통과.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/cheer/arena/controls/joystick.tsx
git commit -m "feat(fe): arena 모바일 조이스틱"
```

---

## Task 9: arena-stage (Canvas + 이동 루프 + 카메라 추적 + HUD)

**Files:**
- Create: `frontend/src/cheer/arena/arena-stage.tsx`

- [ ] **Step 1: 스테이지 조립**

```tsx
// frontend/src/cheer/arena/arena-stage.tsx
import { Canvas, useFrame, useThree } from "@react-three/fiber"
import { ArrowLeft } from "lucide-react"
import { useRef } from "react"
import * as THREE from "three"
import { Joystick } from "./controls/joystick"
import { clampToArena, type MoveInput, useKeyboardInput } from "./controls/use-movement"
import { usePresence } from "./presence/use-presence"
import { type ArenaTeam } from "./presence/types"
import { Avatar } from "./scene/avatar"
import { Stadium } from "./scene/stadium"

const SPEED = 5 // m/s

function World({ inputRef, myTeam }: { inputRef: React.MutableRefObject<MoveInput>; myTeam: ArenaTeam }) {
  const { players, me, move } = usePresence("나", myTeam)
  const pos = useRef({ x: me.x, z: me.z, rotation: me.rotation })
  const { camera } = useThree()

  useFrame((_, dt) => {
    const inp = inputRef.current
    if (inp.x !== 0 || inp.z !== 0) {
      const nx = pos.current.x + inp.x * SPEED * dt
      const nz = pos.current.z + inp.z * SPEED * dt
      const c = clampToArena(nx, nz)
      pos.current.x = c.x
      pos.current.z = c.z
      pos.current.rotation = Math.atan2(inp.x, inp.z)
      move({ ...c, rotation: pos.current.rotation })
    }
    // 3인칭 추적 카메라
    const camTarget = new THREE.Vector3(pos.current.x, 1, pos.current.z)
    const desired = new THREE.Vector3(pos.current.x, 7, pos.current.z + 11)
    camera.position.lerp(desired, Math.min(1, dt * 3))
    camera.lookAt(camTarget)
  })

  return (
    <>
      <Stadium />
      {players.map((p) => (
        <Avatar key={p.id} player={p} />
      ))}
    </>
  )
}

export function ArenaStage({ onExit, myTeam }: { onExit: () => void; myTeam: ArenaTeam }) {
  const inputRef = useKeyboardInput()
  return (
    <div className="cheer-reveal fixed inset-0 z-40 bg-gradient-to-b from-[#bfe3ff] to-[#7fc3f0]">
      <Canvas shadows camera={{ position: [0, 7, 17], fov: 55 }}>
        <fog attach="fog" args={["#bfe3ff", 25, 60]} />
        <World inputRef={inputRef} myTeam={myTeam} />
      </Canvas>

      {/* HUD */}
      <button
        type="button"
        onClick={onExit}
        className="absolute right-4 top-4 inline-flex items-center gap-1.5 rounded-full bg-white/90 px-4 py-2 text-sm font-extrabold text-[var(--c-ink)] shadow-md"
      >
        <ArrowLeft size={16} /> 나가기
      </button>
      <div className="pointer-events-none absolute left-1/2 top-4 -translate-x-1/2 rounded-full bg-black/40 px-4 py-1.5 text-xs font-bold text-white backdrop-blur-sm">
        WASD·방향키로 이동 · 팀 유니폼 입은 팬들과 함께 응원하세요
      </div>
      <Joystick inputRef={inputRef} />
    </div>
  )
}
```

- [ ] **Step 2: Lint**

Run: `cd frontend && bun run lint`
Expected: 통과.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/cheer/arena/arena-stage.tsx
git commit -m "feat(fe): arena 스테이지(캔버스+카메라+HUD)"
```

---

## Task 10: 커뮤니티 페이지 통합

**Files:**
- Modify: `frontend/src/routes/cheer/community.tsx`

- [ ] **Step 1: Stage 타입에 `arena` 추가 + import**

`community.tsx` 상단 import에 추가:
```tsx
import { ArenaStage } from "@/cheer/arena/arena-stage"
```
`type Stage = "invite" | "room" | "measuring" | "result"` →
```tsx
type Stage = "invite" | "room" | "measuring" | "result" | "arena"
```

- [ ] **Step 2: arena 분기 추가**

`CommunityPage`의 분기 return들 사이에 추가(예: `if (stage === "result")` 아래):
```tsx
  if (stage === "arena")
    return (
      <ArenaStage
        onExit={() => setStage("room")}
        myTeam={{ name: TODAY_MATCH.away.name, color: "var(--c-primary)" }}
      />
    )
```
주: `var(--c-primary)`는 three 머티리얼에서 안 통하므로 실제 hex로 넣는다. `TODAY_MATCH.away`의 팀 컬러 필드가 있으면 그걸 쓰고, 없으면 `"#e11d48"` 같은 hex 사용. 구현 시 `mock.ts`의 팀 color 필드 확인 후 반영.

- [ ] **Step 3: Room에 입장 버튼 추가**

`Room` 컴포넌트의 battle CTA 블록 아래(또는 fortune 위)에 섹션 추가:
```tsx
      {/* arena 입장 */}
      <button
        type="button"
        onClick={onEnterArena}
        className="flex w-full items-center justify-between rounded-[26px] bg-[var(--c-ink)] p-6 text-left text-white shadow-[var(--shadow-float)]"
      >
        <div>
          <h2 className="text-xl font-black">🏟️ 응원 스타디움 입장</h2>
          <p className="mt-1 text-sm text-white/80">3D 경기장에서 다른 팬들과 함께 돌아다니며 응원해요</p>
        </div>
        <span className="text-2xl">→</span>
      </button>
```
`Room`의 props를 `{ onStart }`에서 `{ onStart, onEnterArena }`로 확장하고, `CommunityPage`의 `return <Room onStart={startBattle} />`를 `return <Room onStart={startBattle} onEnterArena={() => setStage("arena")} />`로 수정.

- [ ] **Step 4: Lint**

Run: `cd frontend && bun run lint`
Expected: 통과.

- [ ] **Step 5: 시각 확인**

Run: `cd frontend && bun run dev` (또는 이미 실행 중이면 생략)
확인:
1. 커뮤니티 → "응원 스타디움 입장" 버튼 보임.
2. 클릭 → 3D 경기장 뜸.
3. WASD/방향키로 내 아바타 이동, 카메라 따라옴.
4. 봇들이 배회 + 가끔 말풍선.
5. 모든 아바타가 팀명 라벨/유니폼 색.
6. 나가기 → 커뮤니티 복귀.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes/cheer/community.tsx
git commit -m "feat(fe): 커뮤니티에 응원 스타디움 입장 연결"
```

---

## Task 11: 최종 점검

- [ ] **Step 1: 전체 lint**

Run: `cd frontend && bun run lint`
Expected: 통과.

- [ ] **Step 2: 빌드 확인(선택)**

Run: `cd frontend && bun run build`
Expected: 타입 에러 없이 빌드 성공.

- [ ] **Step 3: 데모 시나리오 수동 확인**

스펙 "완료 기준" 1~6 전부 확인.

---

## Self-Review 결과 (작성자 체크)

- **Spec coverage:** 진입 흐름(T10), 3D 씬(T5), 아바타+팀 유니폼/팀명(T6), 조작 키보드(T7)·조이스틱(T8)·카메라(T9), presence 추상화(T2~T4), 의존성(T1) — 스펙 전 항목 태스크 매핑됨.
- **Placeholder scan:** mock.ts의 TEAMS/COMMUNITY_FEED 실제 export 구조는 구현 직전 grep으로 확인하도록 명시(그 외 TBD 없음).
- **Type consistency:** `Player`/`MoveInput`/`ArenaTeam`/`PresenceApi`/`clampToArena`/`usePresence` 시그니처가 T2~T9에서 일관.
- **열린 항목:** 팀 color가 mock.ts에 hex로 있는지 — 있으면 사용, 없으면 팀별 hex 상수 추가(T4 `arenaTeams`에서 처리).
