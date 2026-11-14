import { createFileRoute, Link } from "@tanstack/react-router"
import { CalendarDays, ChevronRight, Lock, MessageCircle } from "lucide-react"
import { useEffect, useState } from "react"
import {
  Avatar,
  Pill,
  RankBadge,
  SectionCard,
  SectionTitle,
} from "@/cheer/components/primitives"
import {
  type AppliedMatch,
  COMMUNITY_FEED,
  DEFEAT_RANKING,
  formatCountdown,
  formatKDate,
  formatTime,
  type InvitationState,
  pct,
  type RankingEntry,
  VICTORY_RANKING,
} from "@/cheer/data/mock"
import {
  entryState,
  useAppliedMatches,
} from "@/cheer/hooks/use-applied-matches"

export const Route = createFileRoute("/cheer/")({
  component: HomePage,
})

function HomePage() {
  return (
    <div className="cheer-reveal space-y-6">
      {/* top bar */}
      <div className="flex items-center justify-between">
        <Pill>오늘의 응원</Pill>
      </div>

      {/* hero banner */}
      <HeroBanner />

      {/* rankings */}
      <div className="grid gap-5 lg:grid-cols-2">
        <RankingCard
          variant="defeat"
          title="오늘의 패배요정 랭킹"
          question="패배율이 가장 높은 유저는 누구일까요?"
          emoji="🌧️"
          data={DEFEAT_RANKING}
        />
        <RankingCard
          variant="victory"
          title="오늘의 승리요정 랭킹"
          question="승률이 가장 높은 유저는 누구일까요?"
          emoji="👑"
          data={VICTORY_RANKING}
        />
      </div>

      {/* feed + CTA */}
      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <SectionCard>
          <SectionTitle
            icon={
              <MessageCircle size={18} className="text-[var(--c-primary)]" />
            }
            right={
              <Link
                to="/cheer/community"
                className="flex items-center gap-1 text-xs font-bold text-[var(--c-primary)]"
              >
                <span className="mr-1 inline-flex items-center gap-1 text-[var(--c-win)]">
                  <span className="size-2 rounded-full bg-[var(--c-win)]" />{" "}
                  14명 참여 중
                </span>
                채팅방 입장 <ChevronRight size={14} />
              </Link>
            }
          >
            실시간 응원
          </SectionTitle>
          <ul className="space-y-3">
            {COMMUNITY_FEED.map((m) => (
              <li key={m.nickname} className="flex items-center gap-3">
                <Avatar emoji={m.emoji} size={34} />
                <div className="min-w-0 flex-1">
                  <span className="text-sm font-extrabold">{m.nickname}</span>
                  <span className="ml-2 text-sm text-[var(--c-ink-soft)]">
                    {m.text}
                  </span>
                </div>
                <span className="shrink-0 text-xs text-[var(--c-muted)]">
                  {m.ago}
                </span>
              </li>
            ))}
          </ul>
        </SectionCard>

        <div className="relative overflow-hidden rounded-[22px] cheer-hero p-6 text-white shadow-[var(--shadow-card)]">
          <div className="relative z-10">
            <div className="mb-3 text-5xl">🏆</div>
            <h4 className="text-lg font-black leading-snug">
              오늘도 응원하고,
              <br />
              랭킹에 도전해보세요!
            </h4>
            <p className="mt-1 text-sm text-white/80">
              함께하는 응원이 더 재밌어요
            </p>
            <Link
              to="/cheer/community"
              className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-white px-4 py-2 text-sm font-extrabold text-[var(--c-primary-700)]"
            >
              응원하러 가기 <ChevronRight size={15} />
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

// 홈 상단 배너. 내 관람 신청 중 가장 가까운(첫 번째) 경기로 채운다.
// 신청 내역이 없으면 캘린더(신청)로 안내하고, 아직 입장 시간이 아니면 버튼을 비활성화한다.
function HeroBanner() {
  const { data: applied, isLoading } = useAppliedMatches()
  const [now, setNow] = useState(() => new Date())

  // 입장 활성화 시각(1분 경계)을 놓치지 않도록 30초마다 재평가
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30_000)
    return () => clearInterval(id)
  }, [])

  // 경기 시작 오름차순이므로 첫 번째가 가장 가까운 경기
  const first = applied?.[0]

  return (
    <div className="relative overflow-hidden rounded-[26px] cheer-hero p-6 text-white shadow-[var(--shadow-float)]">
      <div className="relative z-10">
        {first ? (
          <EnteredBanner applied={first} state={entryState(first, now)} />
        ) : isLoading ? (
          <LoadingBanner />
        ) : (
          <EmptyBanner />
        )}
      </div>
      <div className="pointer-events-none absolute -right-6 -top-10 size-40 rounded-full bg-white/10 blur-2xl" />
    </div>
  )
}

// 신청한 경기가 있을 때: 가장 가까운 경기 정보 + 입장 상태
function EnteredBanner({
  applied,
  state,
}: {
  applied: AppliedMatch
  state: InvitationState
}) {
  const { match, cheeredTeam } = applied
  const statusLabel = !state.canEnter
    ? `⏰ ${formatCountdown(state.minutesUntil)}`
    : state.started
      ? "🔴 LIVE"
      : "✅ 입장 가능"

  return (
    <div className="flex items-center justify-between gap-4">
      <div className="min-w-0">
        <span className="inline-flex items-center rounded-full bg-white/20 px-3 py-1 text-xs font-black">
          {statusLabel}
        </span>
        <h2 className="mt-2 text-2xl font-black tracking-tight">
          {match.home.name} <span className="opacity-70">vs</span>{" "}
          {match.away.name}
        </h2>
        <p className="mt-1 text-sm font-semibold text-white/80">
          {formatKDate(match.kickoffAt)} {formatTime(match.kickoffAt)} ·{" "}
          {match.league} · 📣 {cheeredTeam.name} 응원
        </p>
        {state.canEnter ? (
          <Link
            to="/cheer/community"
            className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-white px-5 py-2.5 text-sm font-extrabold text-[var(--c-primary-700)] shadow-md transition-transform hover:scale-[1.03]"
          >
            입장하기 <ChevronRight size={16} />
          </Link>
        ) : (
          <button
            type="button"
            disabled
            className="mt-4 inline-flex cursor-not-allowed items-center gap-1.5 rounded-full bg-white/20 px-5 py-2.5 text-sm font-extrabold text-white/80"
          >
            <Lock size={14} /> {formatTime(applied.enterOpensAt)}부터 입장 가능
          </button>
        )}
      </div>
    </div>
  )
}

// 신청 내역이 없을 때: 캘린더로 안내
function EmptyBanner() {
  return (
    <div className="flex items-center justify-between gap-4">
      <div className="min-w-0">
        <span className="inline-flex items-center rounded-full bg-white/20 px-3 py-1 text-xs font-black">
          🎟️ 입장 초대장
        </span>
        <h2 className="mt-2 text-2xl font-black tracking-tight">
          아직 신청한 경기가 없어요
        </h2>
        <p className="mt-1 text-sm font-semibold text-white/80">
          캘린더에서 보고 싶은 경기를 골라 응원 신청을 해보세요
        </p>
        <Link
          to="/cheer/calendar"
          className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-white px-5 py-2.5 text-sm font-extrabold text-[var(--c-primary-700)] shadow-md transition-transform hover:scale-[1.03]"
        >
          <CalendarDays size={16} /> 신청하러 가기
        </Link>
      </div>
    </div>
  )
}

// 로딩 중: 레이아웃 유지용 스켈레톤
function LoadingBanner() {
  return (
    <div className="animate-pulse">
      <div className="h-6 w-20 rounded-full bg-white/20" />
      <div className="mt-2 h-7 w-56 rounded-lg bg-white/20" />
      <div className="mt-2 h-4 w-40 rounded bg-white/15" />
      <div className="mt-4 h-10 w-32 rounded-full bg-white/20" />
    </div>
  )
}

function RankingCard({
  variant,
  title,
  question,
  emoji,
  data,
}: {
  variant: "victory" | "defeat"
  title: string
  question: string
  emoji: string
  data: RankingEntry[]
}) {
  const isVictory = variant === "victory"
  const accent = isVictory ? "var(--c-primary)" : "var(--c-lose)"
  const soft = isVictory ? "var(--c-primary-50)" : "var(--c-lose-soft)"
  return (
    <SectionCard className="relative overflow-hidden">
      <div className="pointer-events-none absolute -right-4 -top-4 text-7xl opacity-10">
        {emoji}
      </div>
      <div className="mb-3 flex items-start justify-between">
        <div>
          <h3 className="flex items-center gap-1.5 text-[16px] font-black">
            <span>{emoji}</span> {title}
          </h3>
          <p className="mt-0.5 text-xs text-[var(--c-ink-soft)]">{question}</p>
        </div>
        <Pill color={accent} bg={soft}>
          실시간
        </Pill>
      </div>
      <ul className="space-y-1.5">
        {data.map((e) => (
          <li
            key={e.rank}
            className="flex items-center gap-3 rounded-2xl px-2.5 py-2"
            style={e.rank === 1 ? { background: soft } : undefined}
          >
            <div className="w-6 text-center">
              <RankBadge rank={e.rank} />
            </div>
            <Avatar
              emoji={e.emoji}
              size={34}
              ring={e.rank === 1 ? accent : undefined}
            />
            <span className="flex-1 truncate text-sm font-extrabold">
              {e.nickname}
            </span>
            <span className="text-base font-black" style={{ color: accent }}>
              {pct(e.rate)}
            </span>
            <span className="w-16 text-right text-xs text-[var(--c-muted)]">
              {e.wins} / {e.played} 경기
            </span>
          </li>
        ))}
      </ul>
    </SectionCard>
  )
}
