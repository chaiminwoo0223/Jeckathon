import { useCallback, useEffect, useRef, useState } from "react"
import type { ArenaTeam, Player, PresenceApi } from "./types"

// 백엔드 공간 WS(v2) 프레임
type WireUser = {
  user_id: string
  nickname: string
  team: ArenaTeam | null
  x: number
  z: number
  r: number
}
type Frame =
  | { type: "snapshot"; me: string; users: WireUser[] }
  | { type: "join"; user: WireUser }
  | { type: "leave"; user_id: string }
  | { type: "moves"; p: Record<string, [number, number, number]> }
  | { type: "say"; user_id: string; text: string }
  | { type: "emote" | "pong" | "error" }

type Remote = Player & { tx: number; tz: number; tr: number }

const NEUTRAL: ArenaTeam = { name: "응원단", color: "#9ca3af" }
const SEND_MS = 100 // move 전송 ≤10Hz (서버도 0.1초마다 마지막 값만 쓴다)
const PING_MS = 25_000
const BUBBLE_MS = 3500
const RETRY_MS = 2000

export function wsUrl(communityId: string, token: string) {
  const base = (import.meta.env.VITE_API_URL || location.origin).replace(
    /^http/,
    "ws",
  )
  return `${base}/api/v1/space/${communityId}/ws?token=${encodeURIComponent(token)}`
}

function toRemote(u: WireUser): Remote {
  return {
    id: u.user_id,
    nickname: u.nickname,
    team: u.team ?? NEUTRAL,
    x: u.x,
    z: u.z,
    rotation: u.r,
    isMe: false,
    tx: u.x,
    tz: u.z,
    tr: u.r,
  }
}

// 각도 보간(최단 방향)
function lerpAngle(a: number, b: number, t: number) {
  const d = Math.atan2(Math.sin(b - a), Math.cos(b - a))
  return a + d * t
}

export function useSocketPresence(
  myNickname: string,
  myTeam: ArenaTeam,
  conn?: { communityId: string; token: string },
): PresenceApi & { say: (text: string) => void } {
  const { communityId, token } = conn!
  const meRef = useRef<Player>({
    id: "me",
    nickname: myNickname,
    team: myTeam,
    x: 0,
    z: 6,
    rotation: Math.PI,
    isMe: true,
  })
  // 내 id는 "me"로 고정(바꾸면 Avatar key가 바뀌어 drei Html이 렌더 중 언마운트된다). 서버 uid는 따로 둔다
  const myUidRef = useRef("")
  const othersRef = useRef<Map<string, Remote>>(new Map())
  const clearAtRef = useRef<Record<string, number>>({})
  const wsRef = useRef<WebSocket | null>(null)
  const dirtyRef = useRef(false)
  const [players, setPlayers] = useState<Player[]>([meRef.current])

  const send = useCallback((msg: object) => {
    const ws = wsRef.current
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg))
  }, [])

  const move = useCallback(
    (next: { x: number; z: number; rotation: number }) => {
      meRef.current = { ...meRef.current, ...next }
      dirtyRef.current = true
    },
    [],
  )

  const say = useCallback(
    (text: string) => send({ type: "say", text: text.slice(0, 60) }),
    [send],
  )

  // 연결. 서버는 비회원/토큰 오류를 accept 전에 닫아서 브라우저에는 1008이 아니라 1006으로 온다.
  // 그래서 한 번도 열린 적 없으면 재연결하지 않고, 열렸다 끊긴 뒤에는 연속 5번까지만 다시 붙는다
  useEffect(() => {
    let closed = false
    let retry = 0
    let fails = 0
    let everOpened = false
    let ping = 0
    const setMessage = (uid: string, text: string) => {
      const id = uid === myUidRef.current ? meRef.current.id : uid
      clearAtRef.current[id] = performance.now() + BUBBLE_MS
      if (id === meRef.current.id)
        meRef.current = { ...meRef.current, message: text }
      const o = othersRef.current.get(id)
      if (o) othersRef.current.set(id, { ...o, message: text })
    }
    const onFrame = (f: Frame) => {
      const others = othersRef.current
      switch (f.type) {
        case "snapshot": {
          others.clear()
          for (const u of f.users) {
            if (u.user_id === f.me) {
              // 첫 접속은 서버가 정한 시작 위치, 재접속은 지금 내 위치를 유지해 보낸다
              const first = !myUidRef.current
              myUidRef.current = u.user_id
              meRef.current = {
                ...meRef.current,
                nickname: u.nickname,
                team: u.team ?? NEUTRAL,
                ...(first ? { x: u.x, z: u.z, rotation: u.r } : {}),
              }
              dirtyRef.current = !first
            } else others.set(u.user_id, toRemote(u))
          }
          break
        }
        case "join":
          if (f.user.user_id !== myUidRef.current)
            others.set(f.user.user_id, toRemote(f.user))
          break
        case "leave":
          others.delete(f.user_id)
          break
        case "moves":
          for (const [uid, [x, z, r]] of Object.entries(f.p)) {
            const o = others.get(uid) // 내 것·모르는 uid는 무시
            if (o) others.set(uid, { ...o, tx: x, tz: z, tr: r })
          }
          break
        case "say":
          setMessage(f.user_id, f.text)
          break
      }
    }
    const connect = () => {
      const ws = new WebSocket(wsUrl(communityId, token))
      wsRef.current = ws
      ws.onmessage = (e) => onFrame(JSON.parse(e.data))
      ws.onopen = () => {
        everOpened = true
        fails = 0
        ping = window.setInterval(() => send({ type: "ping" }), PING_MS)
      }
      ws.onclose = (e) => {
        clearInterval(ping)
        if (closed || e.code === 1008 || ++fails > (everOpened ? 5 : 0)) return
        retry = window.setTimeout(connect, RETRY_MS)
      }
    }
    connect()
    return () => {
      closed = true
      clearTimeout(retry)
      clearInterval(ping)
      wsRef.current?.close()
    }
  }, [communityId, token, send])

  // 프레임 루프: 내 위치 전송(스로틀) + 남 위치 보간 + 말풍선 TTL
  useEffect(() => {
    let raf = 0
    let last = performance.now()
    let lastSent = 0
    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000)
      last = now
      if (dirtyRef.current && now - lastSent >= SEND_MS) {
        const m = meRef.current
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          send({ type: "move", x: m.x, z: m.z, r: m.rotation })
          dirtyRef.current = false
          lastSent = now
        }
      }
      const k = 1 - Math.exp(-dt * 12)
      const clearAt = clearAtRef.current
      for (const [id, t] of Object.entries(clearAt)) {
        if (now < t) continue
        delete clearAt[id]
        if (id === meRef.current.id)
          meRef.current = { ...meRef.current, message: undefined }
      }
      const list: Player[] = [meRef.current]
      for (const [id, o] of othersRef.current) {
        const next = {
          ...o,
          x: o.x + (o.tx - o.x) * k,
          z: o.z + (o.tz - o.z) * k,
          rotation: lerpAngle(o.rotation, o.tr, k),
          message: clearAt[id] != null ? o.message : undefined,
        }
        othersRef.current.set(id, next)
        list.push(next)
      }
      setPlayers(list)
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [send])

  return { players, me: meRef.current, move, say }
}
