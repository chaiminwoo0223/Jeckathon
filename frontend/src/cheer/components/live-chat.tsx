import { Send } from "lucide-react"
import { type FormEvent, useEffect, useRef, useState } from "react"
import { wsUrl } from "@/cheer/arena/presence/socket-presence"
import { playPop } from "@/cheer/lib/sound"
import { COMMUNITY_FEED, ME } from "../data/mock"
import { Avatar, SectionCard } from "./primitives"

interface ChatMsg {
  id: number | string
  nickname: string
  emoji: string
  text: string
  me?: boolean
}

type WireChat = { user_id: string; name: string; text: string; sent_at: string }

const SEED: ChatMsg[] = COMMUNITY_FEED.map((m, i) => ({
  id: i,
  nickname: m.nickname,
  emoji: m.emoji,
  text: m.text,
}))

const PING_MS = 25_000
const RETRY_MS = 2000

// 커뮤니티 공간 WS(`/api/v1/space/{id}/ws`)의 chat. 연결 전·communityId 없음이면 messages가 null.
function useSpaceChat(communityId?: string) {
  const [messages, setMessages] = useState<ChatMsg[] | null>(null)
  const [count, setCount] = useState<number | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const token = localStorage.getItem("access_token")
    if (!communityId || !token) return
    let me = ""
    let stopped = false
    let retry = 0
    const users = new Set<string>()
    const toMsg = (m: WireChat, i: number): ChatMsg => ({
      id: `${m.sent_at}-${m.user_id}-${i}`,
      nickname: m.name,
      emoji: m.user_id === me ? "🐶" : "📣",
      text: m.text,
      me: m.user_id === me,
    })

    const connect = () => {
      const ws = new WebSocket(wsUrl(communityId, token))
      wsRef.current = ws
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        if (msg.type === "snapshot") {
          me = msg.me
          users.clear()
          for (const u of msg.users) users.add(u.user_id)
          setCount(users.size)
          setMessages((msg.chat as WireChat[]).map(toMsg))
        } else if (msg.type === "chat") {
          setMessages((prev) => [
            ...(prev ?? []),
            toMsg(msg, prev?.length ?? 0),
          ])
        } else if (msg.type === "join") {
          users.add(msg.user.user_id)
          setCount(users.size)
        } else if (msg.type === "leave") {
          users.delete(msg.user_id)
          setCount(users.size)
        }
      }
      ws.onclose = (e) => {
        wsRef.current = null
        // 1008: 토큰이 틀리거나 입장하지 않은 커뮤니티 → 다시 붙지 않는다
        if (!stopped && e.code !== 1008)
          retry = window.setTimeout(connect, RETRY_MS)
      }
    }
    connect()
    const ping = window.setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN)
        wsRef.current.send('{"type":"ping"}')
    }, PING_MS)
    return () => {
      stopped = true
      clearTimeout(retry)
      clearInterval(ping)
      wsRef.current?.close()
    }
  }, [communityId])

  const send = (text: string) => {
    const ws = wsRef.current
    if (ws?.readyState !== WebSocket.OPEN) return false
    ws.send(JSON.stringify({ type: "chat", text }))
    return true
  }
  return { messages, count, send }
}

// 커뮤니티 실시간 응원 채팅. communityId가 있으면 공간 WS, 없으면 로컬 데모.
// fill=true면 부모 높이를 꽉 채운다 (영상 높이에 맞출 때).
export function LiveChat({
  heightClass = "h-[320px]",
  fill = false,
  communityId,
  onSend,
}: {
  heightClass?: string
  fill?: boolean
  communityId?: string
  onSend?: (text: string) => void // 메타버스: 말풍선으로도 보낸다
}) {
  const live = useSpaceChat(communityId)
  const [local, setLocal] = useState<ChatMsg[]>(SEED)
  const messages = live.messages ?? local
  const [input, setInput] = useState("")
  const listRef = useRef<HTMLDivElement>(null)

  // biome-ignore lint/correctness/useExhaustiveDependencies: 새 메시지가 추가될 때마다 맨 아래로 스크롤
  useEffect(() => {
    listRef.current?.scrollTo({
      top: listRef.current.scrollHeight,
      behavior: "smooth",
    })
  }, [messages])

  const send = (e: FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text) return
    // 소켓이면 서버가 되돌려 주는 chat으로 목록에 들어온다(직접 추가하면 중복)
    if (!(live.messages && live.send(text))) {
      setLocal((prev) => [
        ...prev,
        { id: prev.length, nickname: ME.nickname, emoji: "🐶", text, me: true },
      ])
    }
    setInput("")
    onSend?.(text)
    playPop()
  }

  return (
    <SectionCard
      className={`flex flex-col ${fill ? "h-full" : ""}`}
      pad={false}
    >
      <div
        className="flex items-center justify-between border-b px-4 py-3"
        style={{ borderColor: "var(--c-line)" }}
      >
        <h3 className="flex items-center gap-1.5 text-[15px] font-black">
          🔥 실시간 응원 채팅
        </h3>
        <span className="flex items-center gap-1 text-xs font-bold text-[var(--c-win)]">
          <span className="size-2 rounded-full bg-[var(--c-win)]" />{" "}
          {live.count ?? 14}명
        </span>
      </div>

      <div
        ref={listRef}
        className={`space-y-3 overflow-y-auto px-4 py-3 ${fill ? "min-h-[300px] flex-1" : heightClass}`}
      >
        {messages.map((m) => (
          <div key={m.id} className="flex items-start gap-2.5">
            <Avatar
              emoji={m.emoji}
              size={30}
              ring={m.me ? "var(--c-primary)" : undefined}
            />
            <div className="min-w-0">
              <p
                className={`text-xs font-extrabold ${m.me ? "text-[var(--c-primary)]" : ""}`}
              >
                {m.nickname}
                {m.me ? " (나)" : ""}
              </p>
              <p className="break-words text-sm text-[var(--c-ink-soft)]">
                {m.text}
              </p>
            </div>
          </div>
        ))}
      </div>

      <form
        onSubmit={send}
        className="flex items-center gap-2 border-t p-3"
        style={{ borderColor: "var(--c-line)" }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="응원 메시지를 입력하세요…"
          className="min-w-0 flex-1 rounded-full bg-[var(--c-surface-2)] px-4 py-2.5 text-sm outline-none placeholder:text-[var(--c-muted)] focus:ring-2 focus:ring-[var(--c-primary-100)]"
        />
        <button
          type="submit"
          className="grid size-10 shrink-0 place-items-center rounded-full bg-[var(--c-primary)] text-white transition-all hover:bg-[var(--c-primary-600)] disabled:opacity-40"
          disabled={!input.trim()}
          aria-label="전송"
        >
          <Send size={16} />
        </button>
      </form>
    </SectionCard>
  )
}
