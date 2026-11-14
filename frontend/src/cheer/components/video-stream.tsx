import { Radio, Volume2, VolumeX } from "lucide-react"
import { useRef, useState } from "react"
import { pickBroadcast } from "../data/broadcasts"
import { STREAM, type Team } from "../data/mock"
import { TeamLogo } from "./primitives"

// 경기 중계 플레이어 (YouTube 삽입).
// 대진(홈·원정 팀)으로 영상을 골라 경기마다 다른 영상이 나온다. 목록과 고르는 규칙은 data/broadcasts.ts.
// 브라우저 자동 재생 정책 때문에 음소거로 시작하고, 소리 버튼은 IFrame API(postMessage)로 켜고 끈다.
function embedUrl(id: string): string {
  const params = new URLSearchParams({
    autoplay: "1",
    mute: "1",
    playsinline: "1",
    loop: "1",
    playlist: id, // loop 은 playlist 가 있어야 동작한다
    controls: "0",
    rel: "0",
    modestbranding: "1",
    enablejsapi: "1",
    origin: window.location.origin,
  })
  return `https://www.youtube-nocookie.com/embed/${id}?${params}`
}

export function VideoStream({
  home,
  away,
  compact = false,
}: {
  home: Team
  away: Team
  compact?: boolean
}) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [muted, setMuted] = useState(true)
  const broadcast = pickBroadcast(home.name, away.name)

  const command = (func: string) =>
    iframeRef.current?.contentWindow?.postMessage(
      JSON.stringify({ event: "command", func, args: [] }),
      "*",
    )

  const toggleMute = () => {
    if (muted) {
      command("unMute")
      command("playVideo")
    } else {
      command("mute")
    }
    setMuted(!muted)
  }

  return (
    <div
      className="relative w-full overflow-hidden rounded-[22px] bg-black shadow-[var(--shadow-card)]"
      style={{ aspectRatio: "16 / 9" }}
    >
      <iframe
        key={broadcast.youtubeId}
        ref={iframeRef}
        src={embedUrl(broadcast.youtubeId)}
        title={broadcast.title}
        className="absolute inset-0 size-full border-0"
        allow="autoplay; encrypted-media; picture-in-picture"
        referrerPolicy="strict-origin-when-cross-origin"
        onLoad={() => setMuted(true)}
      />

      {/* top overlay: LIVE + viewers */}
      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between bg-gradient-to-b from-black/60 to-transparent p-3">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--c-lose)] px-2.5 py-1 text-xs font-black text-white">
          <Radio size={12} className="animate-pulse" /> LIVE
        </span>
        <span className="rounded-full bg-black/40 px-2.5 py-1 text-xs font-bold text-white backdrop-blur">
          👀 {STREAM.viewers.toLocaleString()}명 시청
        </span>
      </div>

      {/* bottom overlay: teams */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-center justify-center gap-3 bg-gradient-to-t from-black/70 to-transparent p-3">
        <div className="flex items-center gap-2">
          <TeamLogo team={home} size={compact ? 22 : 28} />
          <span
            className={
              compact
                ? "text-sm font-black text-white"
                : "font-black text-white"
            }
          >
            {home.short}
          </span>
        </div>
        <span className="rounded-md bg-white/15 px-2 py-0.5 text-xs font-black text-white">
          1 : 0
        </span>
        <div className="flex items-center gap-2">
          <span
            className={
              compact
                ? "text-sm font-black text-white"
                : "font-black text-white"
            }
          >
            {away.short}
          </span>
          <TeamLogo team={away} size={compact ? 22 : 28} />
        </div>
      </div>

      {/* mute toggle */}
      <button
        type="button"
        onClick={toggleMute}
        className="absolute bottom-3 right-3 grid size-9 place-items-center rounded-full bg-black/45 text-white backdrop-blur transition hover:bg-black/65"
        aria-label={muted ? "소리 켜기" : "소리 끄기"}
      >
        {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
      </button>
    </div>
  )
}
