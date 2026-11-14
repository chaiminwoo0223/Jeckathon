import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft, Check, Download, Pencil, Share2, X } from "lucide-react"
import { useState } from "react"
import { toast } from "sonner"
import { AllMatchesDialog } from "@/cheer/components/all-matches-dialog"
import { Mascot } from "@/cheer/components/mascot"
import {
  Pill,
  ProgressBar,
  SectionCard,
  SectionTitle,
  TeamLogo,
} from "@/cheer/components/primitives"
import {
  formatKDate,
  getProfile,
  loseRate,
  ME,
  ME_PROFILE,
  type PublicProfile,
  pct,
  resultMeta,
  winRate,
} from "@/cheer/data/mock"
import { useMe } from "@/cheer/hooks/use-me"
import { downloadShareCard } from "@/cheer/lib/share-image"
import useAuth from "@/hooks/useAuth"

const RECENT_COUNT = 4
const NICKNAME_MAX = 20

export const Route = createFileRoute("/cheer/mypage")({
  component: MyPage,
  validateSearch: (search: Record<string, unknown>): { u?: number } => {
    const u = Number(search.u)
    return Number.isFinite(u) && u > 0 ? { u } : {}
  },
})

function MyPage() {
  const { u } = Route.useSearch()
  const { user } = useAuth()
  const { data: me } = useMe()
  const profile = (u != null ? getProfile(u) : undefined) ?? ME_PROFILE
  const isOwner = profile.id === ME.id

  // u가 넘어왔지만 존재하지 않는 유저면 안내
  const notFound = u != null && getProfile(u) === undefined

  const [allMatchesOpen, setAllMatchesOpen] = useState(false)

  // 본인 이름은 실제 로그인 사용자 기준, 없으면 목업 닉네임
  const authName =
    me?.nickname || user?.email?.split("@")[0] || ME_PROFILE.nickname
  // 본인 프로필 닉네임 인라인 편집 (목업: 편집 전까지 로그인 이름을 따라감)
  const [editedNick, setEditedNick] = useState<string | null>(null)
  const ownerName = editedNick ?? authName
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState("")
  const displayNickname = isOwner ? ownerName : profile.nickname

  const seasonWinRate = winRate(profile.stats.win, profile.stats.lose)
  const seasonLoseRate = loseRate(profile.stats.win, profile.stats.lose)

  function startEdit() {
    setDraft(ownerName)
    setEditing(true)
  }
  function commitEdit() {
    const next = draft.trim().slice(0, NICKNAME_MAX)
    setEditing(false)
    if (!next || next === ownerName) return
    setEditedNick(next)
    toast.success("닉네임을 변경했어요 ✨")
  }

  if (notFound) {
    return (
      <div className="cheer-reveal grid place-items-center py-24 text-center">
        <Mascot size="xl" />
        <p className="mt-4 text-lg font-black">프로필을 찾을 수 없어요</p>
        <p className="mt-1 text-sm text-[var(--c-muted)]">
          공유받은 링크가 만료되었거나 잘못되었어요.
        </p>
        <Link
          to="/cheer/mypage"
          className="mt-5 inline-flex items-center gap-1.5 rounded-full bg-[var(--c-primary)] px-5 py-2.5 text-sm font-bold text-white"
        >
          <ArrowLeft size={15} /> 내 프로필로
        </Link>
      </div>
    )
  }

  return (
    <div className="cheer-reveal space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {!isOwner && (
            <Link
              to="/cheer/mypage"
              className="inline-flex items-center gap-1 rounded-full bg-[var(--c-surface)] px-3 py-2 text-sm font-bold shadow-sm"
            >
              <ArrowLeft size={15} /> 내 프로필
            </Link>
          )}
          <h1 className="text-2xl font-black tracking-tight">
            {isOwner ? "마이페이지" : `${profile.nickname}님의 프로필`}
          </h1>
        </div>
      </div>

      {/* profile header */}
      <div className="relative overflow-hidden rounded-[26px] cheer-hero p-6 text-white shadow-[var(--shadow-float)]">
        <div className="relative z-10 flex flex-wrap items-center gap-5">
          <Mascot size="xl" float />
          <div className="min-w-0 flex-1">
            <Pill color="#fff" bg="rgba(255,255,255,.18)">
              👑 Lv.{profile.level} {profile.levelTitle}
            </Pill>
            {editing ? (
              <div className="mt-2 flex items-center gap-2">
                <input
                  // biome-ignore lint/a11y/noAutofocus: 편집 시작 시 바로 입력
                  autoFocus
                  value={draft}
                  maxLength={NICKNAME_MAX}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitEdit()
                    if (e.key === "Escape") setEditing(false)
                  }}
                  className="min-w-0 flex-1 rounded-lg bg-white/90 px-2.5 py-1 text-xl font-black text-[var(--c-ink)] outline-none"
                />
                <button
                  type="button"
                  onClick={commitEdit}
                  aria-label="닉네임 저장"
                  className="grid size-8 place-items-center rounded-lg bg-white/25 hover:bg-white/35"
                >
                  <Check size={16} />
                </button>
                <button
                  type="button"
                  onClick={() => setEditing(false)}
                  aria-label="편집 취소"
                  className="grid size-8 place-items-center rounded-lg bg-white/15 hover:bg-white/25"
                >
                  <X size={16} />
                </button>
              </div>
            ) : (
              <h2 className="mt-2 flex items-center gap-2 text-2xl font-black">
                {displayNickname}
                {isOwner && (
                  <button
                    type="button"
                    onClick={startEdit}
                    aria-label="닉네임 편집"
                    className="opacity-70 transition-opacity hover:opacity-100"
                  >
                    <Pencil size={16} />
                  </button>
                )}
              </h2>
            )}
            <p className="text-sm text-white/80">{profile.bio}</p>
            <div className="mt-3 flex items-center gap-2">
              <span className="text-xs font-bold text-white/70">응원팀</span>
              {profile.teams.map((t) => (
                <span
                  key={t.id}
                  className="flex items-center gap-1 rounded-full bg-white/15 py-1 pl-1 pr-2.5 text-xs font-bold"
                >
                  <TeamLogo team={t} size={20} /> {t.name}
                </span>
              ))}
            </div>
          </div>
          <div className="flex gap-6 rounded-2xl bg-white/15 px-5 py-3 backdrop-blur">
            <div className="text-center">
              <p className="text-xs text-white/70">총 응원 경기</p>
              <p className="text-2xl font-black">
                {profile.stats.total}
                <span className="text-sm">경기</span>
              </p>
            </div>
            <div className="h-10 w-px bg-white/25" />
            <div className="text-center">
              <p className="text-xs text-white/70">누적 포인트</p>
              <p className="text-2xl font-black">
                {profile.totalPoints.toLocaleString()}
                <span className="text-sm">P</span>
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* fairy + style */}
      <div className="grid gap-5 lg:grid-cols-3">
        <FairyCard
          kind="victory"
          title="승리요정 뚜비"
          emoji="👑"
          rate={seasonWinRate}
          rateLabel="승률"
          sub={`승리 ${profile.stats.win} / ${profile.stats.win + profile.stats.lose}경기`}
        />
        <FairyCard
          kind="defeat"
          title="패배요정 구름이"
          emoji="🌧️"
          rate={seasonLoseRate}
          rateLabel="패배율"
          sub={`패배 ${profile.stats.lose} / ${profile.stats.win + profile.stats.lose}경기`}
        />
        <SectionCard>
          <SectionTitle icon="📊">
            {isOwner ? "나의 응원 스타일" : "응원 스타일"}
          </SectionTitle>
          <div className="space-y-3.5">
            {profile.style.map((s) => (
              <div key={s.label}>
                <div className="mb-1 flex items-center justify-between text-sm font-bold">
                  <span>
                    {s.emoji} {s.label}
                  </span>
                  <span className="text-[var(--c-primary)]">{s.value}%</span>
                </div>
                <ProgressBar value={s.value / 100} />
              </div>
            ))}
          </div>
        </SectionCard>
      </div>

      {/* records + donut */}
      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <SectionCard>
          <SectionTitle
            icon="⚽"
            right={
              <button
                type="button"
                onClick={() => setAllMatchesOpen(true)}
                className="text-xs font-bold text-[var(--c-primary)] transition-opacity hover:opacity-70"
              >
                전체 보기 →
              </button>
            }
          >
            {isOwner ? "최근 응원한 경기" : "최근 응원 경기"}
          </SectionTitle>
          <ul className="divide-y" style={{ borderColor: "var(--c-line)" }}>
            {profile.records.slice(0, RECENT_COUNT).map((r) => {
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
                    <span className="text-sm font-bold">
                      {r.match.home.name}
                    </span>
                    <TeamLogo team={r.match.home} size={24} />
                    <span className="min-w-12 text-center text-sm font-black">
                      {r.match.homeScore} : {r.match.awayScore}
                    </span>
                    <TeamLogo team={r.match.away} size={24} />
                    <span className="text-sm font-bold">
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
            })}
          </ul>
        </SectionCard>

        <SectionCard>
          <SectionTitle icon="📈">시즌 통계</SectionTitle>
          <div className="flex items-center gap-5">
            <Donut winRate={seasonWinRate} />
            <ul className="space-y-2 text-sm font-bold">
              <StatRow
                color="var(--c-win)"
                label="승리"
                value={`${profile.stats.win}경기`}
              />
              <StatRow
                color="var(--c-lose)"
                label="패배"
                value={`${profile.stats.lose}경기`}
              />
              <StatRow
                color="var(--c-draw)"
                label="무승부"
                value={`${profile.stats.draw}경기`}
              />
            </ul>
          </div>
        </SectionCard>
      </div>

      {/* badges + share */}
      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <SectionCard>
          <SectionTitle
            icon="🏅"
            right={
              <span className="text-xs font-bold text-[var(--c-muted)]">
                {profile.badges.filter((b) => b.acquired).length}개 획득
              </span>
            }
          >
            배지 컬렉션
          </SectionTitle>
          <div className="grid grid-cols-4 gap-3 sm:grid-cols-4">
            {profile.badges.map((b) => (
              <div
                key={b.code}
                className="flex flex-col items-center gap-1 rounded-2xl p-3 text-center transition-all"
                style={{
                  background: b.acquired
                    ? "var(--c-primary-50)"
                    : "var(--c-surface-2)",
                  opacity: b.acquired ? 1 : 0.5,
                  filter: b.acquired ? "none" : "grayscale(1)",
                }}
                title={b.desc}
              >
                <span className="text-3xl">{b.emoji}</span>
                <span className="text-xs font-extrabold leading-tight">
                  {b.name}
                </span>
                <span className="text-[10px] text-[var(--c-muted)]">
                  {b.desc}
                </span>
              </div>
            ))}
          </div>
        </SectionCard>

        <ShareCard
          profile={profile}
          nickname={displayNickname}
          winRate={seasonWinRate}
          isOwner={isOwner}
        />
      </div>

      <AllMatchesDialog
        open={allMatchesOpen}
        onOpenChange={setAllMatchesOpen}
        records={profile.records}
      />
    </div>
  )
}

function FairyCard({
  kind,
  title,
  emoji,
  rate,
  rateLabel,
  sub,
}: {
  kind: "victory" | "defeat"
  title: string
  emoji: string
  rate: number
  rateLabel: string
  sub: string
}) {
  const isV = kind === "victory"
  const grad = isV
    ? "linear-gradient(135deg,#7b5cf5,#a07bff)"
    : "linear-gradient(135deg,#f6a8cf,#f06ba8)"
  return (
    <div
      className="relative overflow-hidden rounded-[22px] p-5 text-white shadow-[var(--shadow-card)]"
      style={{ background: grad }}
    >
      <div className="pointer-events-none absolute -right-3 -top-3 text-7xl opacity-20">
        {emoji}
      </div>
      <div className="relative z-10">
        <p className="flex items-center gap-1.5 text-sm font-extrabold">
          {emoji} {title}
        </p>
        <p className="mt-3 text-sm text-white/80">{rateLabel}</p>
        <p className="text-4xl font-black">{pct(rate)}</p>
        <p className="mt-1 text-xs text-white/80">{sub}</p>
      </div>
    </div>
  )
}

function StatRow({
  color,
  label,
  value,
}: {
  color: string
  label: string
  value: string
}) {
  return (
    <li className="flex items-center gap-2">
      <span className="size-2.5 rounded-full" style={{ background: color }} />
      <span className="w-12 text-[var(--c-ink-soft)]">{label}</span>
      <span>{value}</span>
    </li>
  )
}

function Donut({ winRate }: { winRate: number }) {
  const size = 120
  const r = 48
  const c = 2 * Math.PI * r
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg
        width={size}
        height={size}
        className="-rotate-90"
        role="img"
        aria-label={`승률 ${pct(winRate)}`}
      >
        <title>시즌 승률 도넛</title>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--c-lose-soft)"
          strokeWidth={16}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--c-primary)"
          strokeWidth={16}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - winRate)}
        />
      </svg>
      <div className="absolute inset-0 grid place-content-center text-center">
        <p className="text-xs font-bold text-[var(--c-muted)]">승률</p>
        <p className="text-2xl font-black text-[var(--c-primary)]">
          {pct(winRate)}
        </p>
      </div>
    </div>
  )
}

function ShareCard({
  profile,
  nickname,
  winRate,
  isOwner,
}: {
  profile: PublicProfile
  nickname: string
  winRate: number
  isOwner: boolean
}) {
  const [saving, setSaving] = useState(false)
  const fairyTitle = winRate >= 0.6 ? "승리요정" : "열정요정"

  async function handleShare() {
    if (saving) return
    setSaving(true)
    try {
      await downloadShareCard({
        nickname,
        fairyTitle,
        winRateText: pct(winRate),
        totalMatches: profile.stats.total,
        favoriteTeam: profile.favoriteTeam.name,
        stats: {
          win: profile.stats.win,
          draw: profile.stats.draw,
          lose: profile.stats.lose,
        },
      })
      toast.success("SNS 공유 카드를 저장했어요 📸")
    } catch {
      toast.error("이미지를 만들지 못했어요. 다시 시도해 주세요")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="relative overflow-hidden rounded-[22px] cheer-hero p-6 text-center text-white shadow-[var(--shadow-card)]">
        <p className="text-sm font-bold text-white/80">
          {isOwner ? "나의 응원 기록" : `${nickname}님의 응원 기록`}
        </p>
        <p className="mt-2 text-sm">
          <span className="cheer-shine text-2xl font-black">
            승률 {pct(winRate)}
          </span>
        </p>
        <p className="text-xs text-white/70">{profile.stats.total}경기 응원</p>
        <div className="my-3">
          <Mascot size="lg" float className="mx-auto" />
        </div>
        <p className="text-lg font-black">
          {winRate >= 0.6 ? "👑" : "🔥"} {fairyTitle} {nickname}
        </p>
        <span className="mt-1 inline-flex items-center gap-1 rounded-full bg-white/18 px-3 py-1 text-xs font-bold">
          <TeamLogo team={profile.favoriteTeam} size={16} /> 최애팀{" "}
          {profile.favoriteTeam.name}
        </span>
      </div>
      <button
        type="button"
        onClick={handleShare}
        disabled={saving}
        className="inline-flex items-center justify-center gap-1.5 rounded-2xl bg-[var(--c-primary)] py-3 text-sm font-extrabold text-white transition-all hover:bg-[var(--c-primary-600)] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {saving ? (
          <>
            <Download size={16} className="animate-bounce" /> 카드 만드는 중…
          </>
        ) : (
          <>
            <Share2 size={16} /> SNS 공유 카드 다운로드
          </>
        )}
      </button>
    </div>
  )
}
