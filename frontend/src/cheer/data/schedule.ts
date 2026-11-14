import { useQuery } from "@tanstack/react-query"
import {
  type MatchDetail,
  MatchesService,
  type TeamPublic,
  TeamsService,
} from "@/client"

// 경기 날짜·시각은 한국 시간 기준 (백엔드 MatchDay.date 도 KST)
const KST = "Asia/Seoul"
const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"]
const FALLBACK_COLOR = "#64748b"

export type UiTeam = { id: string; name: string; short: string; color: string }

export function toUiTeam(t: TeamPublic): UiTeam {
  return {
    id: t.id,
    name: t.name,
    short: t.short_name || t.name.slice(0, 3),
    color: t.color || FALLBACK_COLOR,
  }
}

export function useMonthMatches(month: string) {
  return useQuery({
    queryKey: ["matches", "month", month],
    queryFn: async () =>
      (await MatchesService.readMatchesByMonth({ query: { month } })).data,
    staleTime: 60_000,
    retry: 1,
  })
}

export function useTeams() {
  return useQuery({
    queryKey: ["teams"],
    queryFn: async () => (await TeamsService.readTeams()).data.data,
    staleTime: 5 * 60_000,
    retry: 1,
  })
}

// "YYYY-MM-DD" (KST) of now
export function todayKst(): string {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: KST }).format(new Date())
}

// ISO datetime → "YYYY-MM-DD" (KST)
export function kstDate(iso: string): string {
  return new Intl.DateTimeFormat("sv-SE", { timeZone: KST }).format(
    new Date(iso),
  )
}

export function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split("-").map(Number)
  const d = new Date(Date.UTC(y, m - 1 + delta, 1))
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}`
}

// month grid cells (null = padding), Sunday first
export function monthCells(month: string): (string | null)[] {
  const [y, m] = month.split("-").map(Number)
  const startPad = new Date(Date.UTC(y, m - 1, 1)).getUTCDay()
  const days = new Date(Date.UTC(y, m, 0)).getUTCDate()
  const cells: (string | null)[] = Array(startPad).fill(null)
  for (let d = 1; d <= days; d++)
    cells.push(`${month}-${String(d).padStart(2, "0")}`)
  while (cells.length % 7 !== 0) cells.push(null)
  return cells
}

export function weekdayOf(date: string): string {
  const [y, m, d] = date.split("-").map(Number)
  return WEEKDAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()]
}

export function formatDateLabel(date: string): string {
  const [, m, d] = date.split("-").map(Number)
  return `${m}월 ${d}일 (${weekdayOf(date)})`
}

export function formatKickoff(iso: string): string {
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: KST,
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(new Date(iso))
}

export type Outcome = "WIN" | "LOSE" | "DRAW"

// 경기 결과를 특정 팀 입장에서 본다 (점수 없으면 null)
export function outcomeFor(m: MatchDetail, teamId: string): Outcome | null {
  if (m.home_score == null || m.away_score == null) return null
  const mine = m.home_team_id === teamId ? m.home_score : m.away_score
  const theirs = m.home_team_id === teamId ? m.away_score : m.home_score
  if (mine === theirs) return "DRAW"
  return mine > theirs ? "WIN" : "LOSE"
}

export function involves(m: MatchDetail, teamId: string): boolean {
  return m.home_team_id === teamId || m.away_team_id === teamId
}
