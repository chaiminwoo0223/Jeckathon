import type { ReactNode } from "react"
import { cn } from "@/lib/utils"
import { type FairyType, FAIRY_META, type Team } from "../data/mock"

// 흰 라운드 카드 (브랜드 공통 서피스)
export function SectionCard({
  children,
  className,
  pad = true,
}: {
  children: ReactNode
  className?: string
  pad?: boolean
}) {
  return (
    <div
      className={cn(
        "rounded-[22px] border bg-[var(--c-surface)]",
        pad && "p-5",
        className,
      )}
      style={{ borderColor: "var(--c-line)", boxShadow: "var(--shadow-card)" }}
    >
      {children}
    </div>
  )
}

export function SectionTitle({
  icon,
  children,
  right,
}: {
  icon?: ReactNode
  children: ReactNode
  right?: ReactNode
}) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <h3 className="flex items-center gap-2 text-[17px] font-extrabold tracking-tight">
        {icon && <span className="text-xl">{icon}</span>}
        {children}
      </h3>
      {right}
    </div>
  )
}

// 팀 로고 대체 칩 (약어 + 팀 컬러)
export function TeamLogo({ team, size = 32 }: { team: Team; size?: number }) {
  return (
    <div
      className="grid shrink-0 place-items-center rounded-full font-black text-white"
      style={{
        width: size,
        height: size,
        background: `linear-gradient(140deg, ${team.color}, ${team.color}cc)`,
        fontSize: size * 0.3,
        boxShadow: `0 4px 10px -4px ${team.color}99`,
      }}
      title={team.name}
    >
      {team.short}
    </div>
  )
}

export function Pill({
  children,
  color = "var(--c-primary)",
  bg = "var(--c-primary-50)",
  className,
}: {
  children: ReactNode
  color?: string
  bg?: string
  className?: string
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold",
        className,
      )}
      style={{ color, background: bg }}
    >
      {children}
    </span>
  )
}

export function FairyTag({ type, name }: { type: FairyType; name?: string }) {
  const m = FAIRY_META[type]
  return (
    <span className="inline-flex items-center gap-1 font-extrabold" style={{ color: m.color }}>
      <span>{m.emoji}</span>
      {m.label}
      {name ? <span className="text-[var(--c-ink)]"> {name}</span> : null}
    </span>
  )
}

export function ProgressBar({
  value,
  color = "var(--c-primary)",
  track = "var(--c-primary-50)",
  height = 8,
}: {
  value: number // 0~1
  color?: string
  track?: string
  height?: number
}) {
  return (
    <div className="w-full overflow-hidden rounded-full" style={{ background: track, height }}>
      <div
        className="h-full rounded-full transition-[width] duration-700 ease-out"
        style={{ width: `${Math.min(100, Math.max(0, value * 100))}%`, background: color }}
      />
    </div>
  )
}

const RANK_STYLE: Record<number, { ring: string; crown: string }> = {
  1: { ring: "var(--c-gold)", crown: "🥇" },
  2: { ring: "var(--c-silver)", crown: "🥈" },
  3: { ring: "var(--c-bronze)", crown: "🥉" },
}

export function RankBadge({ rank }: { rank: number }) {
  const s = RANK_STYLE[rank]
  if (s) return <span className="text-lg">{s.crown}</span>
  return (
    <span className="grid size-6 place-items-center text-sm font-bold text-[var(--c-muted)]">
      {rank}
    </span>
  )
}

export function Avatar({ emoji, size = 36, ring }: { emoji: string; size?: number; ring?: string }) {
  return (
    <div
      className="grid shrink-0 place-items-center rounded-full bg-[var(--c-surface-2)]"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.5,
        boxShadow: ring ? `0 0 0 2.5px ${ring}` : "inset 0 0 0 1px var(--c-line)",
      }}
    >
      {emoji}
    </div>
  )
}
