import { ChevronRight, Lock, Ticket as TicketIcon } from "lucide-react"
import {
  type AppliedMatch,
  formatCountdown,
  formatKDate,
  formatTime,
  type InvitationState,
} from "@/cheer/data/mock"
import { cn } from "@/lib/utils"
import { TeamLogo } from "./primitives"

const GATES = ["A", "B", "C", "D"]
const ZONES = ["N", "E", "S", "W"]

// 경기 관람 입장권(초대장). 실제 티켓처럼 본권 + 절취선 + 스터브 구조.
export function Ticket({
  applied,
  state,
  onEnter,
}: {
  applied: AppliedMatch
  state: InvitationState
  onEnter: () => void
}) {
  const { match, cheeredTeam } = applied
  const active = state.canEnter
  const gate = GATES[match.id % GATES.length]
  const zone = ZONES[(match.id >> 1) % ZONES.length]
  const seat = 100 + (match.id % 300)

  const stubBg = { background: "linear-gradient(160deg,#8f89a9,#6d6790)" }
  const bandBg = { background: "linear-gradient(120deg,#8f89a9,#6d6790)" }

  return (
    <article
      className={cn(
        "cheer-ticket relative flex overflow-hidden rounded-[22px] transition-all",
        active ? "hover:-translate-y-1" : "grayscale-[0.4]",
      )}
      style={{
        background: "var(--c-surface)",
        border: "1px solid var(--c-line)",
        boxShadow: active ? "var(--shadow-float)" : "var(--shadow-card)",
      }}
    >
      {/* 본권 */}
      <div className="relative min-w-0 flex-1">
        {/* 상단 밴드 */}
        <div
          className={cn(
            "relative overflow-hidden px-5 py-2.5 text-white",
            active && "cheer-hero",
          )}
          style={active ? undefined : bandBg}
        >
          {active && (
            <div className="cheer-holo pointer-events-none absolute inset-0" />
          )}
          <div className="relative z-10 flex items-center justify-between gap-2">
            <span className="flex items-center gap-1.5 text-[11px] font-black uppercase tracking-wider">
              <TicketIcon size={13} /> 입장권 · {match.league}
            </span>
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-[10px] font-black",
                active
                  ? "bg-white text-[var(--c-primary-700)]"
                  : "bg-black/25 text-white",
              )}
            >
              {active
                ? state.started
                  ? "🔴 LIVE"
                  : "✅ 입장 가능"
                : `⏰ ${formatCountdown(state.minutesUntil)}`}
            </span>
          </div>
        </div>

        {/* 본문 */}
        <div className="px-5 py-4">
          <div className="flex items-center gap-2.5">
            <TeamLogo team={match.home} size={40} />
            <span className="text-[11px] font-black text-[var(--c-muted)]">
              VS
            </span>
            <TeamLogo team={match.away} size={40} />
            <div className="ml-1 min-w-0 flex-1">
              <p className="truncate text-[15px] font-black leading-tight">
                {match.home.name}{" "}
                <span className="text-[var(--c-muted)]">vs</span>{" "}
                {match.away.name}
              </p>
              <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-[var(--c-primary-50)] px-2 py-0.5 text-[11px] font-bold text-[var(--c-primary-700)]">
                📣 {cheeredTeam.name} 응원
              </span>
            </div>
          </div>

          <p className="mt-3 text-center text-xs font-bold text-[var(--c-ink-soft)]">
            {formatKDate(match.kickoffAt)} {formatTime(match.kickoffAt)} 킥오프
          </p>

          {/* 좌석 메타 */}
          <div
            className="mt-2 grid grid-cols-3 gap-2 border-t border-dashed pt-3 text-center"
            style={{ borderColor: "var(--c-line)" }}
          >
            <Meta label="GATE" value={gate} />
            <Meta label="ZONE" value={zone} />
            <Meta label="SEAT" value={String(seat)} />
          </div>

          {/* 입장 버튼 */}
          <button
            type="button"
            disabled={!active}
            onClick={onEnter}
            className={cn(
              "mt-4 flex w-full items-center justify-center gap-1.5 rounded-2xl py-3 text-sm font-extrabold transition-all",
              active
                ? "bg-[var(--c-primary)] text-white hover:bg-[var(--c-primary-600)]"
                : "cursor-not-allowed bg-[var(--c-surface-2)] text-[var(--c-muted)]",
            )}
          >
            {active ? (
              <>
                입장하기 <ChevronRight size={16} />
              </>
            ) : (
              <>
                <Lock size={13} /> 경기 1시간 전 입장 가능
              </>
            )}
          </button>
        </div>
      </div>

      {/* 절취선 */}
      <div className="relative w-5 shrink-0">
        <span
          className="absolute left-1/2 top-0 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{ background: "var(--c-bg)" }}
        />
        <span
          className="absolute bottom-0 left-1/2 size-4 -translate-x-1/2 translate-y-1/2 rounded-full"
          style={{ background: "var(--c-bg)" }}
        />
        <span
          className="absolute inset-y-3 left-1/2 w-px -translate-x-1/2 border-l-2 border-dashed"
          style={{ borderColor: "var(--c-line)" }}
        />
      </div>

      {/* 스터브 */}
      <div
        className={cn(
          "relative flex w-[86px] shrink-0 flex-col items-center justify-between py-4 text-white",
          active && "cheer-hero",
        )}
        style={active ? undefined : stubBg}
      >
        {active && (
          <div className="cheer-holo pointer-events-none absolute inset-0" />
        )}
        <span
          className="relative z-10 text-[10px] font-black uppercase tracking-[0.22em]"
          style={{ writingMode: "vertical-rl" }}
        >
          Admit One
        </span>
        <div className="relative z-10 flex flex-col items-center gap-1.5">
          <span className="text-base font-black leading-none">
            {formatTime(match.kickoffAt)}
          </span>
          <div className="cheer-barcode h-7 w-11 text-white/90" />
        </div>
      </div>
    </article>
  )
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-bold tracking-wider text-[var(--c-muted)]">
        {label}
      </p>
      <p className="text-sm font-black">{value}</p>
    </div>
  )
}
