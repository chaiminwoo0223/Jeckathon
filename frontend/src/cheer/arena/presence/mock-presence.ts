import { ARENA_PLAY_RADIUS, type ArenaTeam, type Player } from "./types"

const CHEERS = [
  "가자!!",
  "이겨라 🔥",
  "와아아아",
  "골!! ⚽",
  "오늘 이긴다",
  "파이팅!",
  "💪💪",
  "최고야",
  "같이 외쳐요!",
]

export type Bot = Player & {
  targetX: number
  targetZ: number
  speed: number
  nextTalkAt: number // ms 타임스탬프(이 시각이 되면 말풍선 갱신)
}

function randomPointInArena(rand: () => number) {
  const r = Math.sqrt(rand()) * ARENA_PLAY_RADIUS
  const a = rand() * Math.PI * 2
  return { x: Math.cos(a) * r, z: Math.sin(a) * r }
}

// 봇 생성. teams: 유니폼으로 입을 팀 목록, names: 봇 닉네임.
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

// dt: 초 단위 경과. 봇을 target 쪽으로 이동하고, 도착하면 새 target을 고른다.
// nextTalkAt에 도달하면 말풍선 문구를 세팅(소거 TTL은 hook이 관리).
export function stepBots(
  bots: Bot[],
  dt: number,
  now: number,
  rand: () => number = Math.random,
): Bot[] {
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
      nextTalkAt = now + 5000 + rand() * 9000
    }

    return { ...b, x, z, rotation, targetX, targetZ, message, nextTalkAt }
  })
}
