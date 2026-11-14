import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { AxiosError } from "axios"
import {
  CalendarX2,
  Check,
  ChevronLeft,
  ChevronRight,
  MapPin,
  RotateCw,
  Ticket,
  X,
} from "lucide-react"
import { useMemo, useState } from "react"
import { toast } from "sonner"
import {
  Pill,
  SectionCard,
  SectionTitle,
  TeamLogo,
} from "@/cheer/components/primitives"
import {
  formatDateLabel,
  formatKickoff,
  involves,
  kstDate,
  monthCells,
  type Outcome,
  outcomeFor,
  shiftMonth,
  todayKst,
  toUiTeam,
  type UiTeam,
  useMonthMatches,
  useTeams,
} from "@/cheer/data/schedule"
import { useCheerMatch, useMyCheers } from "@/cheer/hooks/use-my-cheers"
import type { MatchDetail } from "@/client"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/cheer/calendar")({
  component: CalendarPage,
})

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"]

const OUTCOME_META: Record<Outcome, { label: string; color: string }> = {
  WIN: { label: "승", color: "var(--c-win)" },
  LOSE: { label: "패", color: "var(--c-lose)" },
  DRAW: { label: "무", color: "var(--c-draw)" },
}

function CalendarPage() {
  const today = todayKst()
  const [month, setMonth] = useState(today.slice(0, 7))
  const [picked, setPicked] = useState<string | null>(today)
  const [teamId, setTeamId] = useState<string | null>(null)
  const [cheerMatch, setCheerMatch] = useState<MatchDetail | null>(null)
  const navigate = useNavigate()
  const myCheers = useMyCheers().data
  const cheer = useCheerMatch()

  const matchesQuery = useMonthMatches(month)
  const teamsQuery = useTeams()

  const teams = useMemo(
    () =>
      (teamsQuery.data ?? [])
        .map(toUiTeam)
        .sort((a, b) => a.name.localeCompare(b.name, "ko")),
    [teamsQuery.data],
  )
  const focusTeam = teams.find((t) => t.id === teamId) ?? null

  // date → matches (team filter applied)
  const byDate = useMemo(() => {
    const map = new Map<string, MatchDetail[]>()
    for (const day of matchesQuery.data?.days ?? []) {
      const list = teamId
        ? day.matches.filter((m) => involves(m, teamId))
        : day.matches
      if (list.length > 0) map.set(day.date, list)
    }
    return map
  }, [matchesQuery.data, teamId])

  const firstGameDay = [...byDate.keys()].sort()[0]
  const selected = picked?.startsWith(month)
    ? picked
    : today.startsWith(month)
      ? today
      : (firstGameDay ?? `${month}-01`)
  const dayMatches = byDate.get(selected) ?? []

  const summary = useMemo(() => {
    const all = [...byDate.values()].flat()
    const finished = all.filter((m) => m.status === "FINISHED").length
    const record = { WIN: 0, LOSE: 0, DRAW: 0 }
    if (teamId) {
      for (const m of all) {
        const o = outcomeFor(m, teamId)
        if (o) record[o] += 1
      }
    }
    return {
      total: all.length,
      finished,
      upcoming: all.length - finished,
      record,
    }
  }, [byDate, teamId])

  const goMonth = (delta: number) => {
    setMonth((m) => shiftMonth(m, delta))
    setPicked(null)
  }
  const goToday = () => {
    setMonth(today.slice(0, 7))
    setPicked(today)
  }

  const [y, m] = month.split("-").map(Number)

  return (
    <div className="cheer-reveal space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black tracking-tight">캘린더</h1>
          <p className="mt-1 text-sm text-[var(--c-muted)]">
            KBO리그 2026 일정과 결과. 예정된 경기를 눌러 응원팀을 골라 보세요
          </p>
        </div>
      </div>

      <TeamFilter
        teams={teams}
        loading={teamsQuery.isLoading}
        value={teamId}
        onChange={(id) => setTeamId(id)}
      />

      <div className="grid gap-5 lg:grid-cols-[1.5fr_1fr]">
        <SectionCard>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="이전 달"
                onClick={() => goMonth(-1)}
              >
                <ChevronLeft />
              </Button>
              <h2 className="min-w-[7.5rem] text-center text-lg font-black tabular-nums">
                {y}년 {m}월
              </h2>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="다음 달"
                onClick={() => goMonth(1)}
              >
                <ChevronRight />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="ml-1 rounded-full"
                onClick={goToday}
              >
                오늘
              </Button>
            </div>
            {matchesQuery.isSuccess && (
              <MonthSummary focusTeam={focusTeam} summary={summary} />
            )}
          </div>

          <div className="mb-1.5 grid grid-cols-7 text-center text-xs font-bold text-[var(--c-muted)]">
            {WEEKDAYS.map((w, i) => (
              <div
                key={w}
                className={cn(
                  i === 0 && "text-[var(--c-lose)]",
                  i === 6 && "text-[var(--c-primary)]",
                )}
              >
                {w}
              </div>
            ))}
          </div>

          {matchesQuery.isError ? (
            <div className="grid place-items-center gap-3 rounded-2xl bg-[var(--c-surface-2)] py-16 text-center text-sm text-[var(--c-ink-soft)]">
              경기 일정을 불러오지 못했어요
              <Button
                variant="outline"
                size="sm"
                className="rounded-full"
                onClick={() => matchesQuery.refetch()}
              >
                <RotateCw /> 다시 시도
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-7 gap-1 sm:gap-1.5">
              {monthCells(month).map((date, i) =>
                date === null ? (
                  <div key={`pad-${i}`} />
                ) : matchesQuery.isLoading ? (
                  <Skeleton
                    key={date}
                    className="h-14 rounded-xl sm:h-[84px]"
                  />
                ) : (
                  <DayCell
                    key={date}
                    date={date}
                    weekday={i % 7}
                    matches={byDate.get(date) ?? []}
                    focusTeamId={teamId}
                    isToday={date === today}
                    isSelected={date === selected}
                    onSelect={() => setPicked(date)}
                  />
                ),
              )}
            </div>
          )}

          {matchesQuery.isSuccess && summary.total === 0 && (
            <p className="mt-3 text-center text-xs text-[var(--c-muted)]">
              이 달에는 경기가 없어요
            </p>
          )}
          {teamId && matchesQuery.isSuccess && summary.total > 0 && <Legend />}
        </SectionCard>

        <SectionCard>
          <SectionTitle
            right={
              dayMatches.length > 0 && (
                <span className="text-xs font-bold text-[var(--c-muted)]">
                  {dayMatches.length}경기
                </span>
              )
            }
          >
            {formatDateLabel(selected)}
          </SectionTitle>

          {matchesQuery.isLoading ? (
            <div className="space-y-2.5">
              {[0, 1, 2].map((k) => (
                <Skeleton key={k} className="h-[118px] rounded-2xl" />
              ))}
            </div>
          ) : dayMatches.length === 0 ? (
            <div className="grid place-items-center gap-2 py-14 text-center text-sm text-[var(--c-muted)]">
              <CalendarX2 className="size-8 opacity-60" />
              {focusTeam
                ? `이 날은 ${focusTeam.name} 경기가 없어요`
                : "이 날은 경기가 없어요"}
            </div>
          ) : (
            <ul className="space-y-2.5">
              {dayMatches.map((match) => (
                <li key={match.id}>
                  <MatchCard
                    match={match}
                    focusTeamId={teamId}
                    cheeredTeamId={myCheers?.get(match.id)}
                    onCheer={() => setCheerMatch(match)}
                  />
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
          initialTeamId={myCheers?.get(cheerMatch.id)}
          pending={cheer.isPending}
          onConfirm={(team) =>
            cheer.mutate(
              { matchId: cheerMatch.id, teamId: team.id },
              {
                onSuccess: () => {
                  toast.success(`${team.name} 응원 신청 완료!`, {
                    description: "경기 관람 탭에서 입장 초대장을 확인하세요",
                    action: {
                      label: "보러가기",
                      onClick: () => navigate({ to: "/cheer/community" }),
                    },
                  })
                  setCheerMatch(null)
                },
                onError: (err) =>
                  toast.error(
                    err instanceof AxiosError && err.response?.status === 409
                      ? "이미 끝난 경기라 응원할 수 없어요"
                      : "응원 신청에 실패했어요. 다시 시도해 주세요",
                  ),
              },
            )
          }
        />
      )}
    </div>
  )
}

function TeamFilter({
  teams,
  loading,
  value,
  onChange,
}: {
  teams: UiTeam[]
  loading: boolean
  value: string | null
  onChange: (id: string | null) => void
}) {
  const chip =
    "flex shrink-0 items-center gap-1.5 rounded-full border py-1 pr-3 text-sm font-bold transition-colors"
  return (
    <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
      <button
        type="button"
        onClick={() => onChange(null)}
        aria-pressed={value === null}
        className={cn(
          chip,
          "pl-3",
          value === null
            ? "border-[var(--c-primary)] bg-[var(--c-primary)] text-white"
            : "border-[var(--c-line)] bg-[var(--c-surface)] hover:bg-[var(--c-surface-2)]",
        )}
      >
        전체
      </button>
      {loading
        ? [0, 1, 2, 3, 4, 5].map((k) => (
            <Skeleton key={k} className="h-8 w-20 shrink-0 rounded-full" />
          ))
        : teams.map((t) => {
            const on = value === t.id
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => onChange(on ? null : t.id)}
                aria-pressed={on}
                aria-label={t.name}
                className={cn(
                  chip,
                  "pl-1",
                  on
                    ? "border-[var(--c-primary)] bg-[var(--c-primary-50)] text-[var(--c-primary)]"
                    : "border-[var(--c-line)] bg-[var(--c-surface)] hover:bg-[var(--c-surface-2)]",
                )}
              >
                <TeamLogo team={t} size={24} />
                {t.name}
              </button>
            )
          })}
    </div>
  )
}

function MonthSummary({
  focusTeam,
  summary,
}: {
  focusTeam: UiTeam | null
  summary: {
    total: number
    finished: number
    upcoming: number
    record: Record<Outcome, number>
  }
}) {
  if (summary.total === 0) return null
  const { WIN, LOSE, DRAW } = summary.record
  return (
    <div className="flex flex-wrap items-center gap-1.5 text-xs font-bold">
      {focusTeam && summary.finished > 0 && (
        <Pill color="var(--c-ink)" bg="var(--c-surface-2)">
          {WIN}승 {LOSE}패{DRAW > 0 ? ` ${DRAW}무` : ""}
        </Pill>
      )}
      <Pill color="var(--c-ink-soft)" bg="var(--c-surface-2)">
        {summary.total}경기
      </Pill>
      {summary.upcoming > 0 && <Pill>예정 {summary.upcoming}</Pill>}
    </div>
  )
}

function DayCell({
  date,
  weekday,
  matches,
  focusTeamId,
  isToday,
  isSelected,
  onSelect,
}: {
  date: string
  weekday: number
  matches: MatchDetail[]
  focusTeamId: string | null
  isToday: boolean
  isSelected: boolean
  onSelect: () => void
}) {
  const day = Number(date.slice(8))
  const hasGames = matches.length > 0
  const focusMatch = focusTeamId ? matches[0] : undefined
  const rounds = [...new Set(matches.map((m) => m.round_label).filter(Boolean))]

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={isSelected}
      className={cn(
        "flex h-14 flex-col items-center gap-0.5 rounded-xl border p-1 text-left transition-colors sm:h-[84px] sm:items-stretch sm:p-1.5",
        isSelected
          ? "border-[var(--c-primary)] bg-[var(--c-primary-50)]"
          : hasGames
            ? "border-[var(--c-line)] hover:bg-[var(--c-surface-2)]"
            : "border-[var(--c-line)]/50 hover:bg-[var(--c-surface-2)]",
      )}
    >
      <span
        className={cn(
          "grid size-6 place-items-center rounded-full text-xs font-extrabold tabular-nums",
          isToday
            ? "bg-[var(--c-primary)] text-white"
            : !hasGames
              ? "text-[var(--c-muted)]"
              : weekday === 0
                ? "text-[var(--c-lose)]"
                : weekday === 6 && "text-[var(--c-primary)]",
        )}
      >
        {day}
      </span>

      {hasGames && focusMatch && focusTeamId ? (
        <FocusCellBody match={focusMatch} teamId={focusTeamId} />
      ) : hasGames ? (
        <>
          <span className="mt-auto size-1.5 rounded-full bg-[var(--c-primary)] sm:hidden" />
          <span className="mt-auto hidden truncate text-[11px] font-bold text-[var(--c-primary)] sm:block">
            {rounds[0] ?? `${matches.length}경기`}
          </span>
        </>
      ) : null}
    </button>
  )
}

// 팀 필터 모드: 상대 팀 + 결과(또는 시작 시각)
function FocusCellBody({
  match,
  teamId,
}: {
  match: MatchDetail
  teamId: string
}) {
  const isHome = match.home_team_id === teamId
  const opponent = toUiTeam(isHome ? match.away_team : match.home_team)
  const outcome = outcomeFor(match, teamId)
  const mine = isHome ? match.home_score : match.away_score
  const theirs = isHome ? match.away_score : match.home_score

  return (
    <div className="mt-auto flex flex-col items-center gap-0.5 sm:items-start">
      <div className="hidden min-w-0 items-center gap-1 text-[11px] font-bold sm:flex">
        <span className="text-[var(--c-muted)]">{isHome ? "vs" : "@"}</span>
        <span
          className="size-2 shrink-0 rounded-full"
          style={{ background: opponent.color }}
        />
        <span className="truncate">{opponent.name}</span>
      </div>
      {outcome ? (
        <span
          className="text-[11px] font-black tabular-nums"
          style={{ color: OUTCOME_META[outcome].color }}
        >
          {OUTCOME_META[outcome].label}
          <span className="hidden sm:inline">
            {" "}
            {mine}-{theirs}
          </span>
        </span>
      ) : (
        <span className="text-[11px] font-bold tabular-nums text-[var(--c-ink-soft)]">
          <span className="sm:hidden">{opponent.short}</span>
          <span className="hidden sm:inline">
            {formatKickoff(match.kickoff_at)}
          </span>
        </span>
      )}
    </div>
  )
}

function Legend() {
  return (
    <div className="mt-3 flex items-center justify-end gap-3 text-[11px] font-bold text-[var(--c-muted)]">
      {(Object.keys(OUTCOME_META) as Outcome[]).map((o) => (
        <span key={o} className="flex items-center gap-1">
          <span
            className="size-2 rounded-full"
            style={{ background: OUTCOME_META[o].color }}
          />
          {OUTCOME_META[o].label}
        </span>
      ))}
      <span>vs 홈 · @ 원정</span>
    </div>
  )
}

function MatchCard({
  match,
  focusTeamId,
  cheeredTeamId,
  onCheer,
}: {
  match: MatchDetail
  focusTeamId: string | null
  cheeredTeamId?: string
  onCheer: () => void
}) {
  const home = toUiTeam(match.home_team)
  const away = toUiTeam(match.away_team)
  const finished =
    match.status === "FINISHED" &&
    match.home_score != null &&
    match.away_score != null
  const homeScore = match.home_score ?? 0
  const awayScore = match.away_score ?? 0
  const homeWon = finished && homeScore > awayScore
  const awayWon = finished && awayScore > homeScore
  const focusOutcome = focusTeamId ? outcomeFor(match, focusTeamId) : null

  return (
    <div
      className="rounded-2xl border bg-[var(--c-surface)] p-4"
      style={{ borderColor: "var(--c-line)" }}
    >
      <div className="flex items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-1.5">
          <StatusPill status={match.status ?? "SCHEDULED"} />
          {match.round_label && <Pill>{match.round_label}</Pill>}
          {focusOutcome && (
            <Pill color="#fff" bg={OUTCOME_META[focusOutcome].color}>
              {OUTCOME_META[focusOutcome].label}
            </Pill>
          )}
          {cheeredTeamId && (
            <Pill color="var(--c-win)" bg="var(--c-win-soft)">
              <Ticket size={12} /> 신청됨
            </Pill>
          )}
        </div>
        {match.venue && (
          <span className="flex items-center gap-1 font-bold text-[var(--c-muted)]">
            <MapPin size={12} />
            {match.venue}
          </span>
        )}
      </div>

      <div className="mt-3 grid grid-cols-[1fr_auto_1fr] items-center gap-2">
        <TeamSide
          team={away}
          side="원정"
          dim={finished && !awayWon && homeWon}
        />
        <div className="text-center">
          {finished ? (
            <p className="text-2xl font-black tabular-nums">
              <span
                className={cn(!awayWon && homeWon && "text-[var(--c-muted)]")}
              >
                {match.away_score}
              </span>
              <span className="mx-1.5 text-[var(--c-muted)]">:</span>
              <span
                className={cn(!homeWon && awayWon && "text-[var(--c-muted)]")}
              >
                {match.home_score}
              </span>
            </p>
          ) : (
            <>
              <p className="text-xl font-black tabular-nums text-[var(--c-primary)]">
                {formatKickoff(match.kickoff_at)}
              </p>
              <p className="text-[10px] font-bold text-[var(--c-muted)]">VS</p>
            </>
          )}
        </div>
        <TeamSide team={home} side="홈" dim={finished && !homeWon && awayWon} />
      </div>

      {match.status === "SCHEDULED" && (
        <button
          type="button"
          onClick={onCheer}
          className={cn(
            "mt-3 w-full rounded-xl py-2.5 text-sm font-extrabold transition-colors",
            cheeredTeamId
              ? "border border-[var(--c-primary)] text-[var(--c-primary)] hover:bg-[var(--c-primary-50)]"
              : "bg-[var(--c-primary)] text-white hover:bg-[var(--c-primary-600)]",
          )}
        >
          {cheeredTeamId
            ? `${cheeredTeamId === match.home_team_id ? home.name : away.name} 응원 중 · 바꾸기`
            : "이 경기 응원하기"}
        </button>
      )}
    </div>
  )
}

function TeamSide({
  team,
  side,
  dim,
}: {
  team: UiTeam
  side: "홈" | "원정"
  dim: boolean
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-1.5 text-center",
        dim && "opacity-55",
      )}
    >
      <TeamLogo team={team} size={40} />
      <div>
        <p className="text-sm font-extrabold leading-tight">{team.name}</p>
        <p className="text-[10px] font-bold text-[var(--c-muted)]">{side}</p>
      </div>
    </div>
  )
}

function StatusPill({
  status,
}: {
  status: NonNullable<MatchDetail["status"]>
}) {
  if (status === "LIVE")
    return (
      <Pill color="#fff" bg="var(--c-lose)">
        LIVE
      </Pill>
    )
  if (status === "FINISHED")
    return (
      <Pill color="var(--c-ink-soft)" bg="var(--c-surface-2)">
        종료
      </Pill>
    )
  return <Pill>예정</Pill>
}

function CheerDialog({
  match,
  onClose,
  onConfirm,
  initialTeamId,
  pending,
}: {
  match: MatchDetail
  onClose: () => void
  onConfirm: (team: UiTeam) => void
  initialTeamId?: string
  pending: boolean
}) {
  const [picked, setPicked] = useState<string | null>(initialTeamId ?? null)
  const teams = [toUiTeam(match.away_team), toUiTeam(match.home_team)]
  const pickedTeam = teams.find((t) => t.id === picked)

  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4">
      <button
        type="button"
        aria-label="닫기"
        onClick={onClose}
        className="absolute inset-0 bg-black/40"
      />
      <div className="cheer-pop relative z-10 w-full max-w-sm overflow-hidden rounded-[26px] bg-[var(--c-surface)] shadow-2xl">
        <div className="relative h-28 cheer-hero">
          <button
            type="button"
            aria-label="닫기"
            onClick={onClose}
            className="absolute right-3 top-3 grid size-8 place-items-center rounded-full bg-white/20 text-white hover:bg-white/30"
          >
            <X size={16} />
          </button>
        </div>
        <div className="p-6">
          <h3 className="text-center text-lg font-black">
            {match.away_team.name}{" "}
            <span className="text-[var(--c-muted)]">@</span>{" "}
            {match.home_team.name}
          </h3>
          <p className="mt-1 text-center text-xs text-[var(--c-muted)]">
            {formatDateLabel(kstDate(match.kickoff_at))}{" "}
            {formatKickoff(match.kickoff_at)}
            {match.venue && ` · ${match.venue}`}
          </p>

          <p className="mb-3 mt-5 text-center text-sm font-bold text-[var(--c-ink-soft)]">
            어떤 팀을 응원하나요?
          </p>
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
                    on
                      ? "border-[var(--c-primary)] bg-[var(--c-primary-50)]"
                      : "border-[var(--c-line)]",
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
            disabled={!pickedTeam || pending}
            onClick={() => pickedTeam && onConfirm(pickedTeam)}
            className="mt-6 w-full rounded-2xl bg-[var(--c-primary)] py-3.5 text-sm font-extrabold text-white transition-all hover:bg-[var(--c-primary-600)] disabled:opacity-40"
          >
            {pending ? "신청 중..." : "응원 신청하기"}
          </button>
        </div>
      </div>
    </div>
  )
}
