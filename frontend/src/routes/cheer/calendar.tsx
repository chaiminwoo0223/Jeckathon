import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { Check, ChevronLeft, ChevronRight, Ticket, X } from "lucide-react"
import { useMemo, useState } from "react"
import { toast } from "sonner"
import { Pill, SectionCard, SectionTitle, TeamLogo } from "@/cheer/components/primitives"
import { formatKDate, formatTime, type Match, MATCH_DAYS, MATCHES, type Team, TODAY } from "@/cheer/data/mock"
import { applyToMatch, useAppliedMatches } from "@/cheer/hooks/use-applied-matches"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/cheer/calendar")({
  component: CalendarPage,
})

const YEAR = 2026
const MONTH = 10 // 0-indexed → 11월
const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"]

function CalendarPage() {
  const navigate = useNavigate()
  const [selected, setSelected] = useState(TODAY)
  const [cheerMatch, setCheerMatch] = useState<Match | null>(null)
  const applied = useAppliedMatches()
  const appliedIds = useMemo(() => new Set(applied.map((a) => a.match.id)), [applied])

  const cells = useMemo(() => {
    const first = new Date(YEAR, MONTH, 1)
    const startPad = first.getDay()
    const daysInMonth = new Date(YEAR, MONTH + 1, 0).getDate()
    const arr: (number | null)[] = Array(startPad).fill(null)
    for (let d = 1; d <= daysInMonth; d++) arr.push(d)
    while (arr.length % 7 !== 0) arr.push(null)
    return arr
  }, [])

  const dayMatches = MATCHES.filter((m) => m.kickoffAt.slice(0, 10) === selected)

  const keyOf = (d: number) => `${YEAR}-${String(MONTH + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`

  return (
    <div className="cheer-reveal space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-black tracking-tight">캘린더</h1>
        <Pill>응원할 경기를 골라보세요</Pill>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
        {/* month grid */}
        <SectionCard>
          <div className="mb-4 flex items-center justify-between px-1">
            <button type="button" className="grid size-8 place-items-center rounded-full hover:bg-[var(--c-surface-2)]">
              <ChevronLeft size={18} />
            </button>
            <h2 className="text-lg font-black">{YEAR}년 11월</h2>
            <button type="button" className="grid size-8 place-items-center rounded-full hover:bg-[var(--c-surface-2)]">
              <ChevronRight size={18} />
            </button>
          </div>

          <div className="mb-2 grid grid-cols-7 text-center text-xs font-bold text-[var(--c-muted)]">
            {WEEKDAYS.map((w, i) => (
              <div key={w} className={cn(i === 0 && "text-[var(--c-lose)]")}>{w}</div>
            ))}
          </div>

          <div className="grid grid-cols-7 gap-1">
            {cells.map((d, i) => {
              if (d === null) return <div key={`e${i}`} />
              const k = keyOf(d)
              const count = MATCH_DAYS[k]
              const isSel = k === selected
              const isSun = i % 7 === 0
              return (
                <button
                  key={k}
                  type="button"
                  onClick={() => setSelected(k)}
                  className={cn(
                    "relative mx-auto grid aspect-square w-full max-w-[44px] place-items-center rounded-2xl text-sm font-bold transition-all",
                    isSel
                      ? "bg-[var(--c-primary)] text-white shadow-md"
                      : "hover:bg-[var(--c-surface-2)]",
                    !isSel && isSun && "text-[var(--c-lose)]",
                  )}
                >
                  {d}
                  {count && (
                    <span className="absolute bottom-1 flex gap-0.5">
                      {Array.from({ length: Math.min(count, 3) }).map((_, j) => (
                        <span
                          key={j}
                          className="size-1 rounded-full"
                          style={{ background: isSel ? "#fff" : "var(--c-primary)" }}
                        />
                      ))}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </SectionCard>

        {/* day matches */}
        <SectionCard>
          <SectionTitle>
            {formatKDate(`${selected}T00:00:00`)} 경기 {dayMatches.length}개
          </SectionTitle>
          {dayMatches.length === 0 ? (
            <div className="grid place-content-center gap-2 py-12 text-center text-sm text-[var(--c-muted)]">
              <span className="text-3xl">🗓️</span>
              이 날은 등록된 경기가 없어요
            </div>
          ) : (
            <ul className="space-y-2.5">
              {dayMatches.map((m) => (
                <li key={m.id}>
                  <button
                    type="button"
                    onClick={() => setCheerMatch(m)}
                    className="flex w-full items-center gap-3 rounded-2xl border bg-[var(--c-surface)] p-3 text-left transition-all hover:-translate-y-0.5 hover:shadow-[var(--shadow-card)]"
                    style={{ borderColor: "var(--c-line)" }}
                  >
                    <div className="flex items-center gap-2">
                      <TeamLogo team={m.home} size={30} />
                      <span className="text-xs font-bold text-[var(--c-muted)]">VS</span>
                      <TeamLogo team={m.away} size={30} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-extrabold">
                        {m.home.name} <span className="text-[var(--c-muted)]">vs</span> {m.away.name}
                      </p>
                      <p className="text-xs text-[var(--c-muted)]">{m.league}</p>
                    </div>
                    {appliedIds.has(m.id) && (
                      <Pill color="var(--c-win)" bg="var(--c-win-soft)">
                        <Ticket size={12} /> 신청됨
                      </Pill>
                    )}
                    <span className="shrink-0 text-sm font-black text-[var(--c-primary)]">{formatTime(m.kickoffAt)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>
      </div>

      {cheerMatch && (
        <CheerDialog
          match={cheerMatch}
          onClose={() => setCheerMatch(null)}
          onConfirm={(team) => {
            applyToMatch(cheerMatch.id, team.id)
            toast.success(`${team.name} 응원 신청 완료! 🎟️`, {
              description: "경기 관람 탭에서 입장 초대장을 확인하세요",
              action: { label: "보러가기", onClick: () => navigate({ to: "/cheer/community" }) },
            })
            setCheerMatch(null)
          }}
        />
      )}
    </div>
  )
}

function CheerDialog({
  match,
  onClose,
  onConfirm,
}: {
  match: Match
  onClose: () => void
  onConfirm: (team: Team) => void
}) {
  const [picked, setPicked] = useState<number | null>(null)
  const teams = [match.home, match.away]

  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4">
      <button type="button" aria-label="닫기" onClick={onClose} className="absolute inset-0 bg-black/40" />
      <div className="cheer-pop relative z-10 w-full max-w-sm overflow-hidden rounded-[26px] bg-[var(--c-surface)] shadow-2xl">
        <div className="relative h-28 cheer-hero">
          <button
            type="button"
            onClick={onClose}
            className="absolute right-3 top-3 grid size-8 place-items-center rounded-full bg-white/20 text-white hover:bg-white/30"
          >
            <X size={16} />
          </button>
        </div>
        <div className="p-6">
          <h3 className="text-center text-lg font-black">
            {match.home.name} <span className="text-[var(--c-muted)]">VS</span> {match.away.name}
          </h3>
          <p className="mt-1 text-center text-xs text-[var(--c-muted)]">
            {formatKDate(match.kickoffAt)} {formatTime(match.kickoffAt)} · {match.league}
          </p>

          <p className="mb-3 mt-5 text-center text-sm font-bold text-[var(--c-ink-soft)]">어떤 팀을 응원하나요?</p>
          <div className="grid grid-cols-2 gap-3">
            {teams.map((t) => {
              const on = picked === t.id
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setPicked(t.id)}
                  className={cn(
                    "relative flex flex-col items-center gap-2 rounded-2xl border-2 p-4 transition-all",
                    on ? "border-[var(--c-primary)] bg-[var(--c-primary-50)]" : "border-[var(--c-line)]",
                  )}
                >
                  {on && (
                    <span className="absolute right-2 top-2 grid size-5 place-items-center rounded-full bg-[var(--c-primary)] text-white">
                      <Check size={12} strokeWidth={3} />
                    </span>
                  )}
                  <TeamLogo team={t} size={44} />
                  <span className="text-sm font-extrabold">{t.name}</span>
                </button>
              )
            })}
          </div>

          <button
            type="button"
            disabled={picked === null}
            onClick={() => onConfirm(teams.find((t) => t.id === picked)!)}
            className="mt-6 w-full rounded-2xl bg-[var(--c-primary)] py-3.5 text-sm font-extrabold text-white transition-all hover:bg-[var(--c-primary-600)] disabled:opacity-40"
          >
            응원 신청하기
          </button>
        </div>
      </div>
    </div>
  )
}
