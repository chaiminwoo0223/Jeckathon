import { Send } from "lucide-react"
import { type FormEvent, useEffect, useRef, useState } from "react"
import { playPop } from "@/cheer/lib/sound"
import { Avatar, SectionCard } from "./primitives"
import { COMMUNITY_FEED, ME } from "../data/mock"

interface ChatMsg {
  id: number
  nickname: string
  emoji: string
  text: string
  me?: boolean
}

const SEED: ChatMsg[] = COMMUNITY_FEED.map((m, i) => ({
  id: i,
  nickname: m.nickname,
  emoji: m.emoji,
  text: m.text,
}))

// 커뮤니티 실시간 응원 채팅 (로컬 상태 — 소켓 연동 전 데모).
// fill=true면 부모 높이를 꽉 채운다 (영상 높이에 맞출 때).
export function LiveChat({
  heightClass = "h-[320px]",
  fill = false,
}: {
  heightClass?: string
  fill?: boolean
}) {
  const [messages, setMessages] = useState<ChatMsg[]>(SEED)
  const [input, setInput] = useState("")
  const listRef = useRef<HTMLDivElement>(null)

  // biome-ignore lint/correctness/useExhaustiveDependencies: 새 메시지가 추가될 때마다 맨 아래로 스크롤
  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" })
  }, [messages])

  const send = (e: FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text) return
    setMessages((prev) => [...prev, { id: prev.length, nickname: ME.nickname, emoji: "🐶", text, me: true }])
    setInput("")
    playPop()
  }

  return (
    <SectionCard className={`flex flex-col ${fill ? "h-full" : ""}`} pad={false}>
      <div className="flex items-center justify-between border-b px-4 py-3" style={{ borderColor: "var(--c-line)" }}>
        <h3 className="flex items-center gap-1.5 text-[15px] font-black">🔥 실시간 응원 채팅</h3>
        <span className="flex items-center gap-1 text-xs font-bold text-[var(--c-win)]">
          <span className="size-2 rounded-full bg-[var(--c-win)]" /> 14명
        </span>
      </div>

      <div ref={listRef} className={`space-y-3 overflow-y-auto px-4 py-3 ${fill ? "min-h-[300px] flex-1" : heightClass}`}>
        {messages.map((m) => (
          <div key={m.id} className="flex items-start gap-2.5">
            <Avatar emoji={m.emoji} size={30} ring={m.me ? "var(--c-primary)" : undefined} />
            <div className="min-w-0">
              <p className={`text-xs font-extrabold ${m.me ? "text-[var(--c-primary)]" : ""}`}>
                {m.nickname}{m.me ? " (나)" : ""}
              </p>
              <p className="break-words text-sm text-[var(--c-ink-soft)]">{m.text}</p>
            </div>
          </div>
        ))}
      </div>

      <form onSubmit={send} className="flex items-center gap-2 border-t p-3" style={{ borderColor: "var(--c-line)" }}>
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
