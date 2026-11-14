import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  ArrowLeft,
  CalendarDays,
  Mic,
  Sparkles,
  Ticket as TicketIcon,
  Trophy,
  Users,
} from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { ArenaStage } from "@/cheer/arena/arena-stage"
import { Confetti } from "@/cheer/components/confetti"
import { DecibelMeter } from "@/cheer/components/decibel-meter"
import { LiveChat } from "@/cheer/components/live-chat"
import { Mascot } from "@/cheer/components/mascot"
import {
  Avatar,
  Pill,
  RankBadge,
  SectionCard,
  SectionTitle,
} from "@/cheer/components/primitives"
import { Ticket } from "@/cheer/components/ticket"
import { VideoStream } from "@/cheer/components/video-stream"
import {
  type AppliedMatch,
  BATTLE_PLAYERS,
  BATTLE_REWARDS,
  FORTUNES,
  formatKDate,
  formatTime,
  type Match,
  pct,
  type RankingEntry,
  TEAMS,
  type Team,
  TODAY_MATCH,
} from "@/cheer/data/mock"
import {
  entryState,
  useAppliedMatches,
  useJoinCommunity,
} from "@/cheer/hooks/use-applied-matches"
import { useCountUp } from "@/cheer/hooks/use-count-up"
import { useDecibel } from "@/cheer/hooks/use-decibel"
import { playFanfare, playTick, playWhistle } from "@/cheer/lib/sound"
import { type RankingEntryPublic, RankingsService } from "@/client"

export const Route = createFileRoute("/cheer/community")({
  component: CommunityPage,
})

type Stage = "invite" | "room" | "measuring" | "result" | "arena"
const BATTLE_SECONDS = 20
const TARGET_DB = 90

// API 랭킹 응답에는 아바타 이모지가 없어 순위 기준으로 안정적으로 하나 고른다.
const RANK_EMOJI = ["🦁", "🐯", "🐻", "🐰", "🐱", "🦊", "🐸", "🐧", "🐥", "🐨"]

function toRankingEntry(e: RankingEntryPublic): RankingEntry {
  return {
    rank: e.rank,
    nickname: e.nickname,
    rate: e.rate,
    played: e.played,
    wins: e.win,
    emoji: RANK_EMOJI[(e.rank - 1) % RANK_EMOJI.length],
  }
}

function CommunityPage() {
  const [stage, setStage] = useState<Stage>("invite")
  const [entered, setEntered] = useState<AppliedMatch | null>(null)
  const [remaining, setRemaining] = useState(BATTLE_SECONDS)
  const [finalPeak, setFinalPeak] = useState(0)
  const { db, peak, status, reset } = useDecibel(stage === "measuring")

  const match = entered?.match ?? TODAY_MATCH
  const cheerTeam = entered?.cheeredTeam ?? TEAMS.arsenal

  // countdown
  useEffect(() => {
    if (stage !== "measuring") return
    setRemaining(BATTLE_SECONDS)
    const id = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          clearInterval(id)
          return 0
        }
        return r - 1
      })
    }, 1000)
    return () => clearInterval(id)
  }, [stage])

  // countdown ticks (마지막 3초)
  useEffect(() => {
    if (stage !== "measuring") return
    if (remaining > 0 && remaining <= 3) playTick(remaining === 1)
  }, [stage, remaining])

  // end → result
  useEffect(() => {
    if (stage === "measuring" && remaining === 0) {
      setFinalPeak(peak)
      setStage("result")
    }
  }, [stage, remaining, peak])

  const startBattle = () => {
    reset()
    playWhistle()
    setStage("measuring")
  }

  if (stage === "invite")
    return (
      <InviteList
        onEnter={(am) => {
          setEntered(am)
          setStage("room")
        }}
      />
    )
  if (stage === "measuring")
    return (
      <Measuring
        match={match}
        db={db}
        peak={peak}
        status={status}
        remaining={remaining}
        onCancel={() => setStage("room")}
      />
    )
  if (stage === "result")
    return (
      <Result
        myPeak={finalPeak}
        onAgain={startBattle}
        onBack={() => setStage("room")}
      />
    )
  if (stage === "arena")
    return (
      <ArenaStage
        onExit={() => setStage("room")}
        myNickname={`${cheerTeam.name} 팬`}
        myTeam={{ name: cheerTeam.name, color: cheerTeam.color }}
      />
    )
  return (
    <Room
      match={match}
      cheerTeam={cheerTeam}
      onStart={startBattle}
      onLeave={() => setStage("invite")}
      onEnterArena={() => setStage("arena")}
    />
  )
}

/* ---------------- Invite (입장 초대장) ---------------- */
function InviteList({ onEnter }: { onEnter: (am: AppliedMatch) => void }) {
  const { data: applied, isLoading, isError, refetch } = useAppliedMatches()
  const join = useJoinCommunity()
  const enter = (am: AppliedMatch) =>
    join.mutate(am, { onSuccess: () => onEnter(am) })
  const entering = (am: AppliedMatch) =>
    join.isPending && join.variables?.matchId === am.matchId
  const [now, setNow] = useState(() => new Date())

  // 1분 경계(입장 활성화)를 놓치지 않도록 30초마다 재평가
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000)
    return () => clearInterval(id)
  }, [])

  const items = useMemo(
    () =>
      (applied ?? []).map((am) => ({
        am,
        state: entryState(am, now),
      })),
    [applied, now],
  )
  const open = items.filter((i) => i.state.canEnter)
  const upcoming = items.filter((i) => !i.state.canEnter)

  if (isLoading)
    return (
      <p className="py-20 text-center text-sm font-bold text-[var(--c-muted)]">
        관람 신청 내역을 불러오는 중…
      </p>
    )

  if (isError)
    return (
      <div className="cheer-reveal grid min-h-[50vh] place-content-center gap-3 text-center">
        <p className="text-sm font-bold text-[var(--c-ink-soft)]">
          관람 신청 내역을 불러오지 못했어요
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="mx-auto rounded-full bg-[var(--c-primary)] px-5 py-2 text-sm font-extrabold text-white"
        >
          다시 시도
        </button>
      </div>
    )

  // 신청 내역 없음 → 캘린더로 안내
  if (items.length === 0) {
    return (
      <div className="cheer-reveal grid min-h-[70vh] place-items-center">
        <SectionCard className="relative w-full max-w-md overflow-hidden pt-10 text-center">
          <div className="relative mb-4 flex h-36 items-end justify-center">
            <Mascot size="xl" float flag />
          </div>
          <Pill className="mx-auto">🎟️ 입장 초대장</Pill>
          <h2 className="mt-3 text-2xl font-black leading-snug">
            아직 신청한 경기가 없어요
          </h2>
          <p className="mt-2 text-sm text-[var(--c-ink-soft)]">
            캘린더에서 보고 싶은 경기를 골라 응원 신청을 하면
            <br />
            경기 시작 3시간 전에 입장 초대장이 도착해요!
          </p>
          <Link
            to="/cheer/calendar"
            className="mt-6 inline-flex w-full items-center justify-center gap-1.5 rounded-2xl bg-[var(--c-primary)] py-3.5 text-sm font-extrabold text-white transition-all hover:bg-[var(--c-primary-600)]"
          >
            <CalendarDays size={16} /> 경기 신청하러 가기
          </Link>
        </SectionCard>
      </div>
    )
  }

  return (
    <div className="cheer-reveal space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Pill>🎟️ 입장 초대장</Pill>
          <h1 className="mt-2 text-2xl font-black tracking-tight">
            내 관람 신청 내역
          </h1>
          <p className="text-sm text-[var(--c-muted)]">
            경기 시작 3시간 전부터 입장할 수 있어요
          </p>
        </div>
        <Link
          to="/cheer/calendar"
          className="hidden items-center gap-1.5 rounded-full bg-[var(--c-surface)] px-4 py-2 text-sm font-bold text-[var(--c-primary)] shadow-sm sm:inline-flex"
          style={{ border: "1px solid var(--c-line)" }}
        >
          <CalendarDays size={15} /> 경기 더 신청하기
        </Link>
      </div>

      {/* 지금 입장 가능 */}
      {open.length > 0 && (
        <section className="space-y-3">
          <h2 className="flex items-center gap-1.5 text-sm font-black text-[var(--c-ink-soft)]">
            <span className="size-2 animate-pulse rounded-full bg-[var(--c-win)]" />
            지금 입장할 수 있어요 ({open.length})
          </h2>
          <div className="grid gap-4 lg:grid-cols-2">
            {open.map(({ am, state }) => (
              <Ticket
                key={am.id}
                applied={am}
                state={state}
                onEnter={() => enter(am)}
                entering={entering(am)}
              />
            ))}
          </div>
        </section>
      )}

      {/* 신청했지만 아직 안 열린 경기 */}
      {upcoming.length > 0 && (
        <section className="space-y-3">
          <h2 className="flex items-center gap-1.5 text-sm font-black text-[var(--c-ink-soft)]">
            <TicketIcon size={15} /> 입장 대기 중 ({upcoming.length})
          </h2>
          <div className="grid gap-4 lg:grid-cols-2">
            {upcoming.map(({ am, state }) => (
              <Ticket
                key={am.id}
                applied={am}
                state={state}
                onEnter={() => enter(am)}
                entering={entering(am)}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

/* ---------------- Room ---------------- */
function Room({
  match,
  cheerTeam,
  onStart,
  onLeave,
  onEnterArena,
}: {
  match: Match
  cheerTeam: Team
  onStart: () => void
  onLeave: () => void
  onEnterArena: () => void
}) {
  const fortune = FORTUNES[cheerTeam.id] ?? FORTUNES[TEAMS.arsenal.id]
  // 오늘의 승리요정/패배요정 랭킹 (명세 §4.5, 3초 폴링)
  const victoryQuery = useQuery({
    queryKey: ["rankings", "victory"],
    queryFn: async () => (await RankingsService.readVictoryRanking()).data,
    refetchInterval: 3000,
    retry: 1,
  })
  const defeatQuery = useQuery({
    queryKey: ["rankings", "defeat"],
    queryFn: async () => (await RankingsService.readDefeatRanking()).data,
    refetchInterval: 3000,
    retry: 1,
  })
  const victoryRanking = (victoryQuery.data?.data ?? []).map(toRankingEntry)
  const defeatRanking = (defeatQuery.data?.data ?? []).map(toRankingEntry)
  return (
    <div className="cheer-reveal space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <button
            type="button"
            onClick={onLeave}
            className="mb-1 flex items-center gap-1 text-xs font-bold text-[var(--c-muted)] hover:text-[var(--c-ink-soft)]"
          >
            <ArrowLeft size={14} /> 초대장으로
          </button>
          <Pill>📣 {cheerTeam.name} 응원방</Pill>
          <h1 className="mt-2 text-2xl font-black tracking-tight">
            {match.home.name} vs {match.away.name}
          </h1>
          <p className="text-sm text-[var(--c-muted)]">
            {formatKDate(match.kickoffAt)} {formatTime(match.kickoffAt)} ·{" "}
            {match.league}
          </p>
        </div>
        <Pill color="var(--c-win)" bg="var(--c-win-soft)">
          <Users size={13} className="mr-0.5" /> 5 / 5
        </Pill>
      </div>

      {/* live match stream + chat */}
      <div>
        <SectionTitle icon="📺">경기 생중계</SectionTitle>
        <div className="grid items-start gap-5 lg:grid-cols-[1.7fr_1fr]">
          <VideoStream home={match.home} away={match.away} />
          <LiveChat heightClass="h-[300px]" />
        </div>
      </div>

      {/* battle CTA */}
      <div className="relative overflow-hidden rounded-[26px] cheer-hero p-6 text-white shadow-[var(--shadow-float)]">
        <div className="relative z-10 flex items-center justify-between gap-4">
          <div>
            <h2 className="flex items-center gap-2 text-xl font-black">
              <Trophy size={20} /> 응원 데시벨 대결
            </h2>
            <p className="mt-1 max-w-sm text-sm text-white/85">
              가장 크게 응원하는 3명에게 포인트가 지급돼요. 마이크를 켜고 목청껏
              외쳐보세요!
            </p>
            <button
              type="button"
              onClick={onStart}
              className="mt-4 inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-extrabold text-[var(--c-primary-700)] shadow-md transition-transform hover:scale-[1.03]"
            >
              <Mic size={16} /> 데시벨 대결 시작하기
            </button>
          </div>
          <Mascot size="lg" float className="shrink-0" />
        </div>
      </div>

      {/* arena 입장 */}
      <button
        type="button"
        onClick={onEnterArena}
        className="flex w-full items-center justify-between rounded-[26px] bg-[var(--c-arena)] p-6 text-left text-white shadow-[var(--shadow-float)] transition-transform hover:scale-[1.01]"
      >
        <div>
          <h2 className="text-xl font-black">🏟️ 응원 스타디움 입장</h2>
          <p className="mt-1 max-w-sm text-sm text-white/80">
            3D 경기장에서 팀 유니폼을 입은 다른 팬들과 함께 돌아다니며 응원해요
          </p>
        </div>
        <span className="text-3xl">→</span>
      </button>

      {/* rankings mini */}
      <div className="grid gap-5 lg:grid-cols-2">
        <MiniRanking
          title="오늘의 패배요정 랭킹"
          emoji="🌧️"
          accent="var(--c-lose)"
          soft="var(--c-lose-soft)"
          data={defeatRanking.slice(0, 3)}
        />
        <MiniRanking
          title="오늘의 승리요정 랭킹"
          emoji="👑"
          accent="var(--c-primary)"
          soft="var(--c-primary-50)"
          data={victoryRanking.slice(0, 3)}
        />
      </div>

      {/* fortune */}
      <SectionCard className="relative overflow-hidden">
        <div className="pointer-events-none absolute -right-2 -top-2 text-6xl opacity-15">
          🔮
        </div>
        <SectionTitle
          icon={<Sparkles size={18} className="text-[var(--c-primary)]" />}
        >
          입장 기념 · {cheerTeam.name}의 오늘 운세
        </SectionTitle>
        <div className="rounded-2xl bg-[var(--c-primary-50)] p-4">
          <p className="text-[15px] font-bold text-[var(--c-primary-700)]">
            "{fortune.fortuneText}"
          </p>
          <p className="mt-2 text-sm text-[var(--c-ink-soft)]">
            💡 오늘의 응원 팁: {fortune.cheerTip}
          </p>
        </div>
      </SectionCard>
    </div>
  )
}

function MiniRanking({
  title,
  emoji,
  accent,
  soft,
  data,
}: {
  title: string
  emoji: string
  accent: string
  soft: string
  data: RankingEntry[]
}) {
  return (
    <SectionCard>
      <h3 className="mb-3 flex items-center gap-1.5 text-[15px] font-black">
        <span>{emoji}</span> {title}
      </h3>
      <ul className="space-y-1.5">
        {data.map((e) => (
          <li
            key={e.rank}
            className="flex items-center gap-3 rounded-xl px-2 py-1.5"
            style={e.rank === 1 ? { background: soft } : undefined}
          >
            <div className="w-6 text-center">
              <RankBadge rank={e.rank} />
            </div>
            <Avatar emoji={e.emoji} size={30} />
            <span className="flex-1 truncate text-sm font-bold">
              {e.nickname}
            </span>
            <span className="font-black" style={{ color: accent }}>
              {pct(e.rate)}
            </span>
          </li>
        ))}
      </ul>
    </SectionCard>
  )
}

/* ---------------- Measuring ---------------- */
function Measuring({
  match,
  db,
  peak,
  status,
  remaining,
  onCancel,
}: {
  match: Match
  db: number
  peak: number
  status: string
  remaining: number
  onCancel: () => void
}) {
  // 실시간 순위: 내 peak vs 다른 참가자
  const others = BATTLE_PLAYERS.filter((p) => !p.me)
  const myRank = useMemo(() => {
    const higher = others.filter((p) => p.peakDb > peak).length
    return higher + 1
  }, [peak, others])

  const hitTarget = db >= TARGET_DB
  const mm = String(Math.floor(remaining / 60)).padStart(2, "0")
  const ss = String(remaining % 60).padStart(2, "0")

  return (
    <div className="cheer-reveal space-y-5">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onCancel}
          className="flex items-center gap-1.5 text-sm font-bold text-[var(--c-ink-soft)]"
        >
          <ArrowLeft size={18} /> 데시벨 측정하기
        </button>
        <div className="flex items-center gap-2">
          <Pill
            color={status === "live" ? "var(--c-win)" : "var(--c-primary)"}
            bg={status === "live" ? "var(--c-win-soft)" : "var(--c-primary-50)"}
          >
            {status === "live"
              ? "🎙️ 마이크 측정 중"
              : status === "requesting"
                ? "마이크 권한 요청…"
                : "시뮬레이션 모드"}
          </Pill>
          <span className="rounded-full bg-[var(--c-ink)] px-3 py-1 font-mono text-sm font-bold text-white">
            00:{ss === "00" && mm === "00" ? "00" : ss}
          </span>
        </div>
      </div>

      <div className="grid items-start gap-5 lg:grid-cols-[1.6fr_1fr]">
        {/* main: live stream */}
        <VideoStream home={match.home} away={match.away} />

        {/* side: decibel meter + live chat */}
        <div className="space-y-5">
          <SectionCard className="relative overflow-hidden">
            <div className="flex flex-col items-center py-1">
              <div className="mb-2 flex items-center gap-2 text-center text-xs font-bold text-[var(--c-ink-soft)]">
                <Mascot size="sm" /> 응원 소리로 데시벨을 높여보세요!
              </div>
              <DecibelMeter
                db={db}
                active
                size={220}
                label={hitTarget ? "엄청난 응원이에요! 🔥" : "조금만 더 크게!"}
              />
              <div className="mt-3 flex items-center gap-4">
                <div className="text-center">
                  <p className="text-[11px] font-bold text-[var(--c-muted)]">
                    목표
                  </p>
                  <p className="text-base font-black text-[var(--c-primary)]">
                    {TARGET_DB}dB+
                  </p>
                </div>
                <div className="h-7 w-px bg-[var(--c-line)]" />
                <div className="text-center">
                  <p className="text-[11px] font-bold text-[var(--c-muted)]">
                    내 최고
                  </p>
                  <p className="text-base font-black">{peak.toFixed(1)}dB</p>
                </div>
                <div className="h-7 w-px bg-[var(--c-line)]" />
                <div className="text-center">
                  <p className="text-[11px] font-bold text-[var(--c-muted)]">
                    순위
                  </p>
                  <p className="text-base font-black text-[var(--c-gold)]">
                    {myRank}위
                  </p>
                </div>
              </div>
            </div>
          </SectionCard>
          <LiveChat heightClass="h-[200px]" />
        </div>
      </div>
    </div>
  )
}

/* ---------------- Result ---------------- */
function Result({
  myPeak,
  onAgain,
  onBack,
}: {
  myPeak: number
  onAgain: () => void
  onBack: () => void
}) {
  // 내 기록 반영해 최종 순위 계산
  const standings = useMemo(() => {
    const list = BATTLE_PLAYERS.map((p) =>
      p.me ? { ...p, peakDb: Math.max(p.peakDb, myPeak || p.peakDb) } : p,
    )
    return [...list].sort((a, b) => b.peakDb - a.peakDb)
  }, [myPeak])

  const top3 = standings.slice(0, 3)
  const myIndex = standings.findIndex((p) => p.me)
  const me = standings[myIndex]
  const myPercentile = Math.round(((myIndex + 1) / standings.length) * 100)
  const podiumOrder = [top3[1], top3[0], top3[2]] // 2-1-3
  const myDbCount = useCountUp(me.peakDb, 1400)

  // 🎉 빵빠레 + 함성 (결과 진입 시)
  useEffect(() => {
    playFanfare()
  }, [])

  return (
    <div className="relative space-y-6">
      {/* 화면 플래시 + 폭죽 */}
      <div className="pointer-events-none fixed inset-0 z-10 cheer-flash bg-white" />
      <Confetti count={120} />
      <div
        className="pointer-events-none absolute left-1/2 top-24 z-0 size-64 -translate-x-1/2 rounded-full cheer-burst"
        style={{
          background:
            "radial-gradient(circle, rgba(246,185,59,.6), transparent 70%)",
        }}
      />

      <div className="relative z-20 text-center">
        <h1 className="cheer-title-in text-4xl font-black tracking-tight">
          <span className="cheer-shine">🏁 데시벨 대결 종료!</span>
        </h1>
        <p className="mt-2 text-sm font-semibold text-[var(--c-ink-soft)]">
          가장 크게 응원한 TOP 3에게 포인트가 지급됐어요 🎉
        </p>
      </div>

      <div className="relative z-20 grid gap-5 lg:grid-cols-[1.5fr_1fr]">
        {/* podium */}
        <SectionCard>
          <div className="flex items-end justify-center gap-3 pt-8">
            {podiumOrder.map((p) => {
              const rank =
                p.userId === top3[0].userId
                  ? 1
                  : p.userId === top3[1].userId
                    ? 2
                    : 3
              const h = rank === 1 ? 160 : rank === 2 ? 122 : 98
              const ring =
                rank === 1
                  ? "var(--c-gold)"
                  : rank === 2
                    ? "var(--c-silver)"
                    : "var(--c-bronze)"
              const delay = rank === 1 ? 0.5 : rank === 2 ? 0.2 : 0.35
              return (
                <div
                  key={p.userId}
                  className="flex w-1/3 flex-col items-center"
                >
                  <div
                    className="cheer-bounce-in"
                    style={{ animationDelay: `${delay}s` }}
                  >
                    {rank === 1 && (
                      <div className="mb-1 text-center text-2xl cheer-glow">
                        👑
                      </div>
                    )}
                    <Avatar
                      emoji={p.emoji}
                      size={rank === 1 ? 64 : 48}
                      ring={ring}
                    />
                  </div>
                  <p className="mt-2 truncate text-sm font-extrabold">
                    {p.nickname}
                  </p>
                  <p className="text-sm font-black" style={{ color: ring }}>
                    {p.peakDb.toFixed(1)}dB
                  </p>
                  <div
                    className="cheer-rise mt-2 flex w-full items-start justify-center rounded-t-2xl pt-3 text-2xl font-black"
                    style={{
                      height: h,
                      background: `linear-gradient(${rank === 1 ? "var(--c-primary-100)" : "var(--c-primary-50)"}, var(--c-surface-2))`,
                      color: ring,
                      animationDelay: `${delay + 0.1}s`,
                    }}
                  >
                    <RankBadge rank={rank} />
                  </div>
                </div>
              )
            })}
          </div>
        </SectionCard>

        {/* my record + rewards */}
        <div className="space-y-5">
          <SectionCard className="relative overflow-hidden text-center">
            <div className="pointer-events-none absolute -right-3 -top-3 text-6xl opacity-10">
              📣
            </div>
            <p className="text-xs font-bold text-[var(--c-muted)]">내 기록</p>
            <p className="mt-1 text-5xl font-black text-[var(--c-primary)]">
              {myDbCount.toFixed(1)}
              <span className="text-xl">dB</span>
            </p>
            <Pill className="mx-auto mt-2">상위 {myPercentile}%</Pill>
          </SectionCard>

          <SectionCard>
            <SectionTitle>🎁 보상 지급</SectionTitle>
            <ul className="space-y-2">
              {top3.map((p, i) => (
                <li
                  key={p.userId}
                  className="cheer-slide-in flex items-center gap-3 rounded-xl bg-[var(--c-surface-2)] px-3 py-2"
                  style={{ animationDelay: `${0.6 + i * 0.12}s` }}
                >
                  <RankBadge rank={i + 1} />
                  <Avatar emoji={p.emoji} size={28} />
                  <span className="flex-1 truncate text-sm font-bold">
                    {p.nickname}
                  </span>
                  <span className="font-black text-[var(--c-primary)]">
                    +{BATTLE_REWARDS[i]}P
                  </span>
                </li>
              ))}
            </ul>
          </SectionCard>
        </div>
      </div>

      <div className="relative z-10 flex gap-3">
        <button
          type="button"
          onClick={onBack}
          className="flex-1 rounded-2xl border-2 py-3.5 text-sm font-extrabold text-[var(--c-ink-soft)]"
          style={{ borderColor: "var(--c-line)" }}
        >
          커뮤니티로
        </button>
        <button
          type="button"
          onClick={onAgain}
          className="flex-1 rounded-2xl bg-[var(--c-primary)] py-3.5 text-sm font-extrabold text-white transition-all hover:bg-[var(--c-primary-600)]"
        >
          다시 도전하기
        </button>
      </div>
    </div>
  )
}
