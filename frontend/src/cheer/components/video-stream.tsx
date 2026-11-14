import { Radio, Volume2, VolumeX } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { Mascot } from "./mascot"
import { TeamLogo } from "./primitives"
import { STREAM, type Team } from "../data/mock"

// 경기 중계 스트리밍 플레이어.
// Safari는 HLS 네이티브 재생, 그 외 브라우저는 mp4 프로그레시브 스트리밍으로 폴백.
// 네트워크/소스 오류 시 브랜드 플레이스홀더로 graceful degrade.
export function VideoStream({
  home,
  away,
  compact = false,
}: {
  home: Team
  away: Team
  compact?: boolean
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [muted, setMuted] = useState(true)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    const canHls = v.canPlayType("application/vnd.apple.mpegurl")
    v.src = canHls ? STREAM.hlsUrl : STREAM.mp4Url
    v.play().catch(() => {
      /* autoplay 정책 — muted면 보통 통과, 실패해도 컨트롤로 재생 가능 */
    })
  }, [])

  return (
    <div
      className="relative w-full overflow-hidden rounded-[22px] bg-black shadow-[var(--shadow-card)]"
      style={{ aspectRatio: "16 / 9" }}
    >
      {!failed ? (
        <video
          ref={videoRef}
          className="size-full object-cover"
          autoPlay
          muted={muted}
          loop
          playsInline
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="grid size-full place-content-center place-items-center gap-2 cheer-hero text-white">
          <Mascot size={compact ? "md" : "lg"} float />
          <p className="text-sm font-bold text-white/85">중계 연결 준비 중이에요…</p>
        </div>
      )}

      {/* top overlay: LIVE + scoreboard */}
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
          <span className={compact ? "text-sm font-black text-white" : "font-black text-white"}>{home.short}</span>
        </div>
        <span className="rounded-md bg-white/15 px-2 py-0.5 text-xs font-black text-white">1 : 0</span>
        <div className="flex items-center gap-2">
          <span className={compact ? "text-sm font-black text-white" : "font-black text-white"}>{away.short}</span>
          <TeamLogo team={away} size={compact ? 22 : 28} />
        </div>
      </div>

      {/* mute toggle */}
      {!failed && (
        <button
          type="button"
          onClick={() => {
            const v = videoRef.current
            if (!v) return
            v.muted = !v.muted
            setMuted(v.muted)
            if (!v.muted) v.play().catch(() => {})
          }}
          className="absolute bottom-3 right-3 grid size-9 place-items-center rounded-full bg-black/45 text-white backdrop-blur transition hover:bg-black/65"
          aria-label={muted ? "소리 켜기" : "소리 끄기"}
        >
          {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
        </button>
      )}
    </div>
  )
}
