import { createFileRoute } from "@tanstack/react-router"
import { ArrowLeft, ChevronRight, Mic, Sparkles, Trophy, Users } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { Confetti } from "@/cheer/components/confetti"
import { DecibelMeter } from "@/cheer/components/decibel-meter"
import { LiveChat } from "@/cheer/components/live-chat"
import { Mascot } from "@/cheer/components/mascot"
import { Avatar, Pill, RankBadge, SectionCard, SectionTitle } from "@/cheer/components/primitives"
import { VideoStream } from "@/cheer/components/video-stream"
import { useCountUp } from "@/cheer/hooks/use-count-up"
import { useDecibel } from "@/cheer/hooks/use-decibel"
import { playFanfare, playTick, playWhistle } from "@/cheer/lib/sound"
import {
  BATTLE_PLAYERS,
  BATTLE_REWARDS,
  DEFEAT_RANKING,
  FORTUNES,
  formatTime,
  pct,
  TEAMS,
  TODAY_MATCH,
  VICTORY_RANKING,
} from "@/cheer/data/mock"

export const Route = createFileRoute("/cheer/community")({
  component: CommunityPage,
})

type Stage = "invite" | "room" | "measuring" | "result"
const BATTLE_SECONDS = 20
const TARGET_DB = 90

function CommunityPage() {
  const [stage, setStage] = useState<Stage>("invite")
  const [remaining, setRemaining] = useState(BATTLE_SECONDS)
  const [finalPeak, setFinalPeak] = useState(0)
  const { db, peak, status, reset } = useDecibel(stage === "measuring")

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

  if (stage === "invite") return <Invite onEnter={() => setStage("room")} />
  if (stage === "measuring")
    return <Measuring db={db} peak={peak} status={status} remaining={remaining} onCancel={() => setStage("room")} />
  if (stage === "result")
    return <Result myPeak={finalPeak} onAgain={startBattle} onBack={() => setStage("room")} />
  return <Room onStart={startBattle} />
}

/* ---------------- Invite ---------------- */
function Invite({ onEnter }: { onEnter: () => void }) {
  return (
    <div className="cheer-reveal grid min-h-[70vh] place-items-center">
      <SectionCard className="relative w-full max-w-md overflow-hidden pt-10 text-center">
        <Confetti count={30} />
        <div className="relative mb-4 flex h-40 items-end justify-center">
          <Mascot size="xl" float flag />
        </div>
        <Pill className="mx-auto">초대장 도착 💌</Pill>
        <h2 className="mt-3 text-2xl font-black leading-snug">
          {TODAY_MATCH.away.name} 팬 커뮤니티<br />초대장이 도착했어요!
        </h2>
        <p className="mt-2 text-sm text-[var(--c-ink-soft)]">
          지금 바로 커뮤니티에 입장하고 함께 응원해요!
        </p>
        <button
          type="button"
          onClick={onEnter}
          className="mt-6 inline-flex w-full items-center justify-center gap-1.5 rounded-2xl bg-[var(--c-primary)] py-3.5 text-sm font-extrabold text-white transition-all hover:bg-[var(--c-primary-600)]"
        >
          커뮤니티 입장하기 <ChevronRight size={16} />
        </button>
        <button type="button" className="mt-2 w-full py-2 text-xs font-bold text-[var(--c-muted)]">
          나중에 할게요
        </button>
      </SectionCard>
    </div>
  )
}

/* ---------------- Room ---------------- */
function Room({ onStart }: { onStart: () => void }) {
  const fortune = FORTUNES[TEAMS.arsenal.id]
  return (
    <div className="cheer-reveal space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Pill>오늘의 커뮤니티</Pill>
          <h1 className="mt-2 text-2xl font-black tracking-tight">
            {TODAY_MATCH.home.name} vs {TODAY_MATCH.away.name}
          </h1>
          <p className="text-sm text-[var(--c-muted)]">
            11.14 (금) {formatTime(TODAY_MATCH.kickoffAt)} · {TODAY_MATCH.league}
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
          <VideoStream home={TODAY_MATCH.home} away={TODAY_MATCH.away} />
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
              가장 크게 응원하는 3명에게 포인트가 지급돼요. 마이크를 켜고 목청껏 외쳐보세요!
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

      {/* rankings mini */}
      <div className="grid gap-5 lg:grid-cols-2">
        <MiniRanking title="오늘의 패배요정 랭킹" emoji="🌧️" accent="var(--c-lose)" soft="var(--c-lose-soft)" data={DEFEAT_RANKING.slice(0, 3)} />
        <MiniRanking title="오늘의 승리요정 랭킹" emoji="👑" accent="var(--c-primary)" soft="var(--c-primary-50)" data={VICTORY_RANKING.slice(0, 3)} />
      </div>

      {/* fortune */}
      <SectionCard className="relative overflow-hidden">
        <div className="pointer-events-none absolute -right-2 -top-2 text-6xl opacity-15">🔮</div>
        <SectionTitle icon={<Sparkles size={18} className="text-[var(--c-primary)]" />}>
          입장 기념 · {TODAY_MATCH.away.name}의 오늘 운세
        </SectionTitle>
        <div className="rounded-2xl bg-[var(--c-primary-50)] p-4">
          <p className="text-[15px] font-bold text-[var(--c-primary-700)]">"{fortune.fortuneText}"</p>
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
  data: typeof VICTORY_RANKING
}) {
  return (
    <SectionCard>
      <h3 className="mb-3 flex items-center gap-1.5 text-[15px] font-black">
        <span>{emoji}</span> {title}
      </h3>
      <ul className="space-y-1.5">
        {data.map((e) => (
          <li key={e.rank} className="flex items-center gap-3 rounded-xl px-2 py-1.5" style={e.rank === 1 ? { background: soft } : undefined}>
            <div className="w-6 text-center"><RankBadge rank={e.rank} /></div>
            <Avatar emoji={e.emoji} size={30} />
            <span className="flex-1 truncate text-sm font-bold">{e.nickname}</span>
            <span className="font-black" style={{ color: accent }}>{pct(e.rate)}</span>
          </li>
        ))}
      </ul>
    </SectionCard>
  )
}

/* ---------------- Measuring ---------------- */
function Measuring({
  db,
  peak,
  status,
  remaining,
  onCancel,
}: {
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
        <button type="button" onClick={onCancel} className="flex items-center gap-1.5 text-sm font-bold text-[var(--c-ink-soft)]">
          <ArrowLeft size={18} /> 데시벨 측정하기
        </button>
        <div className="flex items-center gap-2">
          <Pill color={status === "live" ? "var(--c-win)" : "var(--c-primary)"} bg={status === "live" ? "var(--c-win-soft)" : "var(--c-primary-50)"}>
            {status === "live" ? "🎙️ 마이크 측정 중" : status === "requesting" ? "마이크 권한 요청…" : "시뮬레이션 모드"}
          </Pill>
          <span className="rounded-full bg-[var(--c-ink)] px-3 py-1 font-mono text-sm font-bold text-white">
            00:{ss === "00" && mm === "00" ? "00" : ss}
          </span>
        </div>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.5fr_1fr]">
        <SectionCard className="relative overflow-hidden">
          <div className="flex flex-col items-center py-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-bold text-[var(--c-ink-soft)]">
              <Mascot size="sm" /> 응원 소리로 데시벨을 높여보세요!
            </div>
            <DecibelMeter db={db} active label={hitTarget ? "와! 지금 엄청난 응원이에요! 🔥" : "조금만 더 크게!"} />
            <div className="mt-4 flex items-center gap-6">
              <div className="text-center">
                <p className="text-xs font-bold text-[var(--c-muted)]">목표 데시벨</p>
                <p className="text-lg font-black text-[var(--c-primary)]">{TARGET_DB}dB+</p>
              </div>
              <div className="h-8 w-px bg-[var(--c-line)]" />
              <div className="text-center">
                <p className="text-xs font-bold text-[var(--c-muted)]">내 최고</p>
                <p className="text-lg font-black">{peak.toFixed(1)}dB</p>
              </div>
              <div className="h-8 w-px bg-[var(--c-line)]" />
              <div className="text-center">
                <p className="text-xs font-bold text-[var(--c-muted)]">현재 순위</p>
                <p className="text-lg font-black text-[var(--c-gold)]">{myRank}위</p>
              </div>
            </div>
          </div>
        </SectionCard>

        {/* stream + live chat */}
        <div className="space-y-5">
          <VideoStream home={TODAY_MATCH.home} away={TODAY_MATCH.away} compact />
          <LiveChat heightClass="h-[220px]" />
        </div>
      </div>
    </div>
  )
}

/* ---------------- Result ---------------- */
function Result({ myPeak, onAgain, onBack }: { myPeak: number; onAgain: () => void; onBack: () => void }) {
  // 내 기록 반영해 최종 순위 계산
  const standings = useMemo(() => {
    const list = BATTLE_PLAYERS.map((p) => (p.me ? { ...p, peakDb: Math.max(p.peakDb, myPeak || p.peakDb) } : p))
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
      <div className="pointer-events-none absolute left-1/2 top-24 z-0 size-64 -translate-x-1/2 rounded-full cheer-burst" style={{ background: "radial-gradient(circle, rgba(246,185,59,.6), transparent 70%)" }} />

      <div className="relative z-20 text-center">
        <h1 className="cheer-title-in text-4xl font-black tracking-tight">
          <span className="cheer-shine">🏁 데시벨 대결 종료!</span>
        </h1>
        <p className="mt-2 text-sm font-semibold text-[var(--c-ink-soft)]">가장 크게 응원한 TOP 3에게 포인트가 지급됐어요 🎉</p>
      </div>

      <div className="relative z-20 grid gap-5 lg:grid-cols-[1.5fr_1fr]">
        {/* podium */}
        <SectionCard>
          <div className="flex items-end justify-center gap-3 pt-8">
            {podiumOrder.map((p) => {
              const rank = p.userId === top3[0].userId ? 1 : p.userId === top3[1].userId ? 2 : 3
              const h = rank === 1 ? 160 : rank === 2 ? 122 : 98
              const ring = rank === 1 ? "var(--c-gold)" : rank === 2 ? "var(--c-silver)" : "var(--c-bronze)"
              const delay = rank === 1 ? 0.5 : rank === 2 ? 0.2 : 0.35
              return (
                <div key={p.userId} className="flex w-1/3 flex-col items-center">
                  <div className="cheer-bounce-in" style={{ animationDelay: `${delay}s` }}>
                    {rank === 1 && <div className="mb-1 text-center text-2xl cheer-glow">👑</div>}
                    <Avatar emoji={p.emoji} size={rank === 1 ? 64 : 48} ring={ring} />
                  </div>
                  <p className="mt-2 truncate text-sm font-extrabold">{p.nickname}</p>
                  <p className="text-sm font-black" style={{ color: ring }}>{p.peakDb.toFixed(1)}dB</p>
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
            <div className="pointer-events-none absolute -right-3 -top-3 text-6xl opacity-10">📣</div>
            <p className="text-xs font-bold text-[var(--c-muted)]">내 기록</p>
            <p className="mt-1 text-5xl font-black text-[var(--c-primary)]">
              {myDbCount.toFixed(1)}<span className="text-xl">dB</span>
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
                  <span className="flex-1 truncate text-sm font-bold">{p.nickname}</span>
                  <span className="font-black text-[var(--c-primary)]">+{BATTLE_REWARDS[i]}P</span>
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
