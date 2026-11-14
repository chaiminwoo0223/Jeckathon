import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  createFileRoute,
  Link,
  redirect,
  useNavigate,
} from "@tanstack/react-router"
import { type FormEvent, useState } from "react"
import { toast } from "sonner"
import { LoginService } from "@/client"
import { AuthField } from "@/cheer/components/auth-field"
import { Mascot } from "@/cheer/components/mascot"
import { SocialButtons } from "@/cheer/components/social-buttons"
import { isLoggedIn } from "@/hooks/useAuth"
import { handleError } from "@/utils"

export const Route = createFileRoute("/cheer_/login")({
  component: LoginPage,
  beforeLoad: () => {
    if (isLoggedIn()) {
      throw redirect({ to: "/cheer" })
    }
  },
})

function LoginPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [email, setEmail] = useState("")
  const [pw, setPw] = useState("")

  const loginMutation = useMutation({
    mutationFn: async () => {
      const res = await LoginService.loginAccessToken({
        body: { username: email.trim(), password: pw },
      })
      localStorage.setItem("access_token", res.data.access_token)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["currentUser"] })
      toast.success("로그인 완료! 환영해요 📣")
      navigate({ to: "/cheer" })
    },
    onError: handleError.bind(toast.error),
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !pw.trim()) {
      toast.error("이메일과 비밀번호를 입력해주세요.")
      return
    }
    loginMutation.mutate()
  }

  return (
    <AuthShell title="다시 만나서 반가워요!" subtitle="로그인하고 오늘의 경기를 응원해요">
      <form onSubmit={submit} className="space-y-3">
        <AuthField label="이메일" type="email" value={email} onChange={setEmail} placeholder="이메일을 입력하세요" autoComplete="email" />
        <AuthField label="비밀번호" type="password" value={pw} onChange={setPw} placeholder="비밀번호를 입력하세요" autoComplete="current-password" />
        <button
          type="submit"
          disabled={loginMutation.isPending}
          className="mt-1 w-full rounded-2xl bg-[var(--c-primary)] py-3.5 text-sm font-extrabold text-white transition-all hover:bg-[var(--c-primary-600)] disabled:opacity-60"
        >
          {loginMutation.isPending ? "로그인 중..." : "로그인"}
        </button>
      </form>

      <Divider />
      <SocialButtons />

      <p className="mt-6 text-center text-sm text-[var(--c-ink-soft)]">
        아직 회원이 아니신가요?{" "}
        <Link to="/cheer/signup" className="font-extrabold text-[var(--c-primary)]">
          회원가입
        </Link>
      </p>
    </AuthShell>
  )
}

export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
}) {
  return (
    <div className="cheer-scope grid min-h-screen place-items-center px-4 py-10">
      <div className="w-full max-w-[400px]">
        <div className="mb-6 flex flex-col items-center text-center">
          <Mascot size="lg" float />
          <div className="mt-3 flex items-center gap-1.5">
            <span className="text-xl">📣</span>
            <span className="text-xl font-black tracking-tight">
              CHEER<span className="text-[var(--c-primary)]"> 101</span>
            </span>
          </div>
          <h1 className="mt-4 text-2xl font-black tracking-tight">{title}</h1>
          <p className="mt-1 text-sm text-[var(--c-ink-soft)]">{subtitle}</p>
        </div>
        <div
          className="rounded-[26px] border bg-[var(--c-surface)] p-6 shadow-[var(--shadow-float)]"
          style={{ borderColor: "var(--c-line)" }}
        >
          {children}
        </div>
      </div>
    </div>
  )
}

export function Divider() {
  return (
    <div className="my-5 flex items-center gap-3">
      <span className="h-px flex-1 bg-[var(--c-line)]" />
      <span className="text-xs font-bold text-[var(--c-muted)]">또는</span>
      <span className="h-px flex-1 bg-[var(--c-line)]" />
    </div>
  )
}
