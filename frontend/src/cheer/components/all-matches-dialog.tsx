import { useMemo, useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"
import {
  type CheerRecord,
  formatKDate,
  type MatchResult,
  resultMeta,
} from "../data/mock"
import { Pill, TeamLogo } from "./primitives"

type Filter = "ALL" | "WIN" | "DRAW" | "LOSE"

const FILTERS: { key: Filter; label: string }[] = [
  { key: "ALL", label: "전체" },
  { key: "WIN", label: "승리" },
  { key: "DRAW", label: "무승부" },
  { key: "LOSE", label: "패배" },
]

export function AllMatchesDialog({
  open,
  onOpenChange,
  records,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  records: CheerRecord[]
}) {
  const [filter, setFilter] = useState<Filter>("ALL")

  const counts = useMemo(() => {
    const c = { WIN: 0, DRAW: 0, LOSE: 0 } as Record<MatchResult, number>
    for (const r of records) c[r.result] = (c[r.result] ?? 0) + 1
    return c
  }, [records])

  const filtered = useMemo(
    () =>
      filter === "ALL" ? records : records.filter((r) => r.result === filter),
    [records, filter],
  )

  const totalPoints = useMemo(
    () => records.reduce((sum, r) => sum + r.pointsEarned, 0),
    [records],
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        showCloseButton
        className="cheer-scope flex max-h-[85vh] flex-col gap-0 overflow-hidden rounded-[22px] border-0 p-0 sm:max-w-xl"
        style={{ background: "var(--c-surface)" }}
      >
        {/* header */}
        <DialogHeader
          className="shrink-0 space-y-3 border-b p-5 text-left"
          style={{ borderColor: "var(--c-line)" }}
        >
          <DialogTitle className="flex items-center gap-2 text-xl font-black">
            <span className="text-2xl">⚽</span> 전체 응원 경기
          </DialogTitle>
          <div className="flex items-center gap-2 text-xs font-bold text-[var(--c-muted)]">
            <span>
              총 <span className="text-[var(--c-ink)]">{records.length}</span>
              경기
            </span>
            <span className="text-[var(--c-line)]">·</span>
            <span className="text-[var(--c-win)]">{counts.WIN}승</span>
            <span className="text-[var(--c-draw)]">{counts.DRAW}무</span>
            <span className="text-[var(--c-lose)]">{counts.LOSE}패</span>
            <span className="text-[var(--c-line)]">·</span>
            <span>
              누적{" "}
              <span className="text-[var(--c-primary)]">
                +{totalPoints.toLocaleString()}P
              </span>
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((f) => {
              const active = filter === f.key
              return (
                <button
                  key={f.key}
                  type="button"
                  onClick={() => setFilter(f.key)}
                  className={cn(
                    "rounded-full px-3.5 py-1.5 text-xs font-bold transition-colors",
                    active
                      ? "bg-[var(--c-primary)] text-white"
                      : "bg-[var(--c-surface-2)] text-[var(--c-ink-soft)] hover:bg-[var(--c-primary-50)]",
                  )}
                >
                  {f.label}
                </button>
              )
            })}
          </div>
        </DialogHeader>

        {/* list */}
        <ul
          className="min-h-0 flex-1 divide-y overflow-y-auto px-5"
          style={{ borderColor: "var(--c-line)" }}
        >
          {filtered.length === 0 ? (
            <li className="py-12 text-center text-sm font-bold text-[var(--c-muted)]">
              해당하는 경기가 없어요
            </li>
          ) : (
            filtered.map((r) => {
              const rm = resultMeta(r.result)
              return (
                <li key={r.id} className="flex items-center gap-3 py-3">
                  <div className="w-20 shrink-0 text-xs">
                    <p className="font-bold">
                      {formatKDate(r.match.kickoffAt)}
                    </p>
                    <p className="text-[var(--c-muted)]">{r.match.league}</p>
                  </div>
                  <div className="flex flex-1 items-center justify-center gap-2">
                    <span className="hidden text-sm font-bold sm:inline">
                      {r.match.home.name}
                    </span>
                    <TeamLogo team={r.match.home} size={24} />
                    <span className="min-w-12 text-center text-sm font-black">
                      {r.match.homeScore} : {r.match.awayScore}
                    </span>
                    <TeamLogo team={r.match.away} size={24} />
                    <span className="hidden text-sm font-bold sm:inline">
                      {r.match.away.name}
                    </span>
                  </div>
                  <Pill color={rm.color} bg={rm.bg}>
                    {rm.label}
                  </Pill>
                  <span className="w-12 shrink-0 text-right text-xs font-black text-[var(--c-primary)]">
                    +{r.pointsEarned}P
                  </span>
                </li>
              )
            })
          )}
        </ul>
      </DialogContent>
    </Dialog>
  )
}
