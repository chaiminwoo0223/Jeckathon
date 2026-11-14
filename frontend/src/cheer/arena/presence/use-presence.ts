import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { ALL_TEAMS } from "@/cheer/data/mock"
import { type Bot, createBots, stepBots } from "./mock-presence"
import type { ArenaTeam, Player, PresenceApi } from "./types"

const BOT_NAMES = [
  "열혈팬준호",
  "응원요정지수",
  "함성대장",
  "골세레머니",
  "치어리더민",
  "북치는곰",
  "붉은악마",
]

// mock.ts의 팀을 {name,color} 유니폼 정보로 매핑.
function arenaTeams(): ArenaTeam[] {
  return ALL_TEAMS.map((t) => ({ name: t.name, color: t.color }))
}

export function usePresence(
  myNickname: string,
  myTeam: ArenaTeam,
): PresenceApi {
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
  const botsRef = useRef<Bot[]>(createBots(teams, BOT_NAMES, performance.now()))
  const talkClearRef = useRef<Record<string, number>>({})
  const [players, setPlayers] = useState<Player[]>([
    meRef.current,
    ...botsRef.current,
  ])

  const move = useCallback(
    (next: { x: number; z: number; rotation: number }) => {
      meRef.current = { ...meRef.current, ...next }
    },
    [],
  )

  useEffect(() => {
    let raf = 0
    let last = performance.now()
    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000)
      last = now

      const stepped = stepBots(botsRef.current, dt, now)
      // 말풍선 TTL: 새로 생긴 메시지는 3.5초 뒤 제거
      botsRef.current = stepped.map((b) => {
        if (b.message && talkClearRef.current[b.id] == null) {
          talkClearRef.current[b.id] = now + 3500
        }
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
