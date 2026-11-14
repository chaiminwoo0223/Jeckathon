import { createFileRoute } from "@tanstack/react-router"
import { Bell, ChevronRight, Lock, Mic, Monitor, Moon, Plus, Shield, SlidersHorizontal, Sun, Trash2, UserCog, X } from "lucide-react"
import { type ReactNode, useState } from "react"
import { Mascot } from "@/cheer/components/mascot"
import { SectionCard, TeamLogo } from "@/cheer/components/primitives"
import { ME } from "@/cheer/data/mock"
import { type Theme, useTheme } from "@/components/theme-provider"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/cheer/settings")({
  component: SettingsPage,
})

function SettingsPage() {
  const [toggles, setToggles] = useState({
    notifyMatch: true,
    notifyInvite: true,
    notifyRanking: true,
    notifyService: false,
    autoJoin: true,
    rankingPublic: true,
  })
  const set = (k: keyof typeof toggles) => setToggles((t) => ({ ...t, [k]: !t[k] }))
  const { theme, setTheme } = useTheme()

  const THEMES: { value: Theme; label: string; icon: ReactNode }[] = [
    { value: "light", label: "라이트", icon: <Sun size={16} /> },
    { value: "dark", label: "다크", icon: <Moon size={16} /> },
    { value: "system", label: "시스템", icon: <Monitor size={16} /> },
  ]

  return (
    <div className="cheer-reveal space-y-6">
      <h1 className="text-2xl font-black tracking-tight">설정</h1>

      {/* banner */}
      <div className="relative overflow-hidden rounded-[26px] cheer-hero p-6 text-white shadow-[var(--shadow-card)]">
        <div className="relative z-10 flex items-center justify-between">
          <h2 className="text-xl font-black leading-snug">응원 경험을<br />나에게 맞게 설정해 보세요!</h2>
          <Mascot size="lg" float />
        </div>
      </div>

      {/* appearance */}
      <SectionCard>
        <GroupTitle icon={<Sun size={18} />}>화면 설정</GroupTitle>
        <div className="flex items-center justify-between gap-4 py-2">
          <div>
            <p className="text-sm font-bold">테마</p>
            <p className="text-xs text-[var(--c-muted)]">라이트 / 다크 / 시스템 설정을 선택하세요</p>
          </div>
          <div className="flex rounded-full bg-[var(--c-surface-2)] p-1">
            {THEMES.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setTheme(t.value)}
                className={cn(
                  "flex items-center gap-1.5 rounded-full px-3.5 py-2 text-xs font-bold transition-all",
                  theme === t.value ? "bg-[var(--c-primary)] text-white shadow" : "text-[var(--c-ink-soft)]",
                )}
              >
                {t.icon} {t.label}
              </button>
            ))}
          </div>
        </div>
      </SectionCard>

      {/* account */}
      <SectionCard>
        <GroupTitle icon={<UserCog size={18} />}>계정 및 프로필</GroupTitle>
        <div className="divide-y" style={{ borderColor: "var(--c-line)" }}>
          <Row label="닉네임" value={ME.nickname} chevron />
          <Row label="한 줄 소개" value={ME.bio} chevron />
          <div className="flex items-center justify-between py-3.5">
            <span className="text-sm font-bold">응원하는 팀</span>
            <div className="flex items-center gap-2">
              {ME.teams.map((t) => (
                <span key={t.id} className="flex items-center gap-1 rounded-full bg-[var(--c-primary-50)] py-1 pl-1 pr-2 text-xs font-bold text-[var(--c-primary-700)]">
                  <TeamLogo team={t} size={18} /> {t.name}
                  <X size={12} className="ml-0.5 opacity-50" />
                </span>
              ))}
              <button type="button" className="flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-bold text-[var(--c-primary)]" style={{ borderColor: "var(--c-primary-100)" }}>
                <Plus size={12} /> 팀 추가
              </button>
            </div>
          </div>
        </div>
      </SectionCard>

      {/* notifications */}
      <SectionCard>
        <GroupTitle icon={<Bell size={18} />}>알림 설정</GroupTitle>
        <div className="divide-y" style={{ borderColor: "var(--c-line)" }}>
          <ToggleRow icon="📅" label="경기 일정 알림" desc="응원하는 팀의 경기 시작 전에 알려드려요" on={toggles.notifyMatch} onToggle={() => set("notifyMatch")} />
          <ToggleRow icon="📣" label="커뮤니티 초대 알림" desc="응원방 개설, 데시벨 대결 시작 알림을 받아요" on={toggles.notifyInvite} onToggle={() => set("notifyInvite")} />
          <ToggleRow icon="🏆" label="랭킹 및 보상 알림" desc="승리요정/패배요정 랭킹, 배지 획득, 포인트 적립" on={toggles.notifyRanking} onToggle={() => set("notifyRanking")} />
          <ToggleRow icon="🎉" label="서비스 소식 및 이벤트" desc="신규 기능, 이벤트, 특별 미션 소식을 받아요" on={toggles.notifyService} onToggle={() => set("notifyService")} />
        </div>
      </SectionCard>

      {/* cheer & community */}
      <SectionCard>
        <GroupTitle icon={<SlidersHorizontal size={18} />}>응원 및 커뮤니티</GroupTitle>
        <div className="divide-y" style={{ borderColor: "var(--c-line)" }}>
          <ToggleRow icon="👥" label="커뮤니티 참여 기본 설정" desc="경기 당일 자동으로 커뮤니티에 입장할까요?" on={toggles.autoJoin} onToggle={() => set("autoJoin")} />
          <Row icon={<Mic size={16} className="text-[var(--c-primary)]" />} label="데시벨 대결 마이크 권한" value="" desc="응원 데시벨 측정을 위해 마이크 사용을 허용해요" chevron />
          <ToggleRow icon="📊" label="랭킹 공개 여부" desc="내 승률/패배율을 커뮤니티 랭킹에 노출할까요?" on={toggles.rankingPublic} onToggle={() => set("rankingPublic")} />
        </div>
      </SectionCard>

      {/* security */}
      <SectionCard>
        <GroupTitle icon={<Shield size={18} />}>개인정보 및 보안</GroupTitle>
        <div className="divide-y" style={{ borderColor: "var(--c-line)" }}>
          <Row icon={<Lock size={16} className="text-[var(--c-ink-soft)]" />} label="계정 연동" desc="SNS 계정을 연결해 간편하게 로그인해요" value="G  🍎  💬" chevron />
          <Row label="비밀번호 변경" value="" chevron />
          <div className="flex items-center justify-between py-3.5">
            <span className="flex items-center gap-2 text-sm font-bold text-[var(--c-lose)]"><Trash2 size={15} /> 계정 탈퇴</span>
            <ChevronRight size={16} className="text-[var(--c-muted)]" />
          </div>
        </div>
      </SectionCard>
    </div>
  )
}

function GroupTitle({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <h3 className="mb-2 flex items-center gap-2 text-[16px] font-black">
      <span className="grid size-7 place-items-center rounded-lg bg-[var(--c-primary-50)] text-[var(--c-primary)]">{icon}</span>
      {children}
    </h3>
  )
}

function Row({
  icon,
  label,
  value,
  desc,
  chevron,
}: {
  icon?: ReactNode
  label: string
  value: string
  desc?: string
  chevron?: boolean
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-3.5">
      <div className="flex min-w-0 items-center gap-2">
        {icon}
        <div className="min-w-0">
          <p className="text-sm font-bold">{label}</p>
          {desc && <p className="truncate text-xs text-[var(--c-muted)]">{desc}</p>}
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {value && <span className="max-w-[220px] truncate text-sm text-[var(--c-ink-soft)]">{value}</span>}
        {chevron && <ChevronRight size={16} className="text-[var(--c-muted)]" />}
      </div>
    </div>
  )
}

function ToggleRow({
  icon,
  label,
  desc,
  on,
  onToggle,
}: {
  icon: string
  label: string
  desc: string
  on: boolean
  onToggle: () => void
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-3.5">
      <div className="flex min-w-0 items-center gap-2.5">
        <span className="text-lg">{icon}</span>
        <div className="min-w-0">
          <p className="text-sm font-bold">{label}</p>
          <p className="text-xs text-[var(--c-muted)]">{desc}</p>
        </div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={on}
        onClick={onToggle}
        className={cn("relative h-7 w-12 shrink-0 rounded-full transition-colors", on ? "bg-[var(--c-primary)]" : "bg-[var(--c-line)]")}
      >
        <span className={cn("absolute top-1 size-5 rounded-full bg-white shadow transition-all", on ? "left-6" : "left-1")} />
      </button>
    </div>
  )
}
