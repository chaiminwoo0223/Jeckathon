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
