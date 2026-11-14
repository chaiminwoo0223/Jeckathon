import { createFileRoute, Link, Outlet } from "@tanstack/react-router"
import { CalendarDays, Home, LogOut, Moon, Settings, Sun, Trophy, User } from "lucide-react"
import { Mascot } from "@/cheer/components/mascot"
import { useTheme } from "@/components/theme-provider"
import { cn } from "@/lib/utils"

export const Route = createFileRoute("/cheer")({
  component: CheerLayout,
})

const NAV = [
  { to: "/cheer", label: "홈", icon: Home, exact: true },
  { to: "/cheer/calendar", label: "캘린더", icon: CalendarDays },
  { to: "/cheer/community", label: "커뮤니티", icon: Trophy },
  { to: "/cheer/mypage", label: "마이페이지", icon: User },
  { to: "/cheer/settings", label: "설정", icon: Settings },
]

function CheerLayout() {
  const { resolvedTheme, setTheme } = useTheme()
  const isDark = resolvedTheme === "dark"
  return (
    <div className="cheer-scope flex min-h-screen w-full">
      {/* Sidebar */}
      <aside className="sticky top-0 flex h-screen w-[232px] shrink-0 flex-col border-r bg-[var(--c-surface)]/70 px-4 py-6 backdrop-blur-xl"
        style={{ borderColor: "var(--c-line)" }}>
        <div className="mb-8 flex items-center gap-2 px-2">
          <span className="text-2xl">📣</span>
          <span className="text-xl font-black leading-none tracking-tight">
            CHEER
            <span className="text-[var(--c-primary)]"> 101</span>
          </span>
        </div>

        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map(({ to, label, icon: Icon, exact }) => (
            <Link
              key={to}
              to={to}
              activeOptions={{ exact: !!exact }}
              className="group"
            >
              {({ isActive }) => (
                <div
                  className={cn(
                    "flex items-center gap-3 rounded-2xl px-3.5 py-3 text-[15px] font-bold transition-all",
                    isActive
                      ? "bg-[var(--c-primary-50)] text-[var(--c-primary-700)]"
                      : "text-[var(--c-ink-soft)] hover:bg-[var(--c-surface-2)]",
                  )}
                >
                  <Icon size={20} strokeWidth={2.4} />
                  {label}
                </div>
              )}
            </Link>
          ))}
        </nav>

        <div className="mt-4 rounded-3xl bg-[var(--c-primary-50)] p-4 text-center">
          <Mascot size="md" float className="mx-auto" />
          <p className="mt-2 text-sm font-extrabold text-[var(--c-primary-700)]">오늘도 응원해요!</p>
        </div>

        <button
          type="button"
          onClick={() => setTheme(isDark ? "light" : "dark")}
          className="mt-3 flex items-center justify-center gap-2 rounded-2xl py-2.5 text-sm font-bold text-[var(--c-ink-soft)] hover:bg-[var(--c-surface-2)]"
          aria-label="테마 전환"
        >
          {isDark ? <Sun size={16} /> : <Moon size={16} />}
          {isDark ? "라이트 모드" : "다크 모드"}
        </button>

        <Link
          to="/cheer/login"
          className="mt-1 flex items-center justify-center gap-2 rounded-2xl py-2.5 text-sm font-bold text-[var(--c-muted)] hover:bg-[var(--c-surface-2)]"
        >
          <LogOut size={16} /> 로그아웃
        </Link>
      </aside>

      {/* Content */}
      <main className="min-w-0 flex-1 px-7 py-7 lg:px-10">
        <div className="mx-auto w-full max-w-[1120px]">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
