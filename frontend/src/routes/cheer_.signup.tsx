import { useMutation } from "@tanstack/react-query"
import {
  createFileRoute,
  Link,
  redirect,
  useNavigate,
} from "@tanstack/react-router"
import { type FormEvent, useState } from "react"
import { toast } from "sonner"
import { UsersService } from "@/client"
import { AuthField } from "@/cheer/components/auth-field"
import { SocialButtons } from "@/cheer/components/social-buttons"
import { isLoggedIn } from "@/hooks/useAuth"
import { handleError } from "@/utils"
import { AuthShell, Divider } from "./cheer_.login"

export const Route = createFileRoute("/cheer_/signup")({
  component: SignupPage,
  beforeLoad: () => {
    if (isLoggedIn()) {
      throw redirect({ to: "/cheer" })
    }
  },
})

function SignupPage() {
  const navigate = useNavigate()
  const [nickname, setNickname] = useState("")
  const [email, setEmail] = useState("")
  const [pw, setPw] = useState("")
  const [pw2, setPw2] = useState("")

  const signUpMutation = useMutation({
    mutationFn: () =>
      UsersService.registerUser({
        body: { email: email.trim(), password: pw, full_name: nickname.trim() },
      }),
    onSuccess: () => {
      toast.success("회원가입 완료! 로그인해주세요 🎉")
      navigate({ to: "/cheer/login" })
    },
    onError: handleError.bind(toast.error),
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!nickname.trim() || !email.trim() || !pw.trim()) {
      toast.error("모든 항목을 입력해주세요.")
      return
    }
    if (pw.length < 8) {
      toast.error("비밀번호는 8자 이상이어야 해요.")
      return
    }
    if (pw !== pw2) {
      toast.error("비밀번호가 일치하지 않아요.")
      return
    }
    signUpMutation.mutate()
  }

  return (
    <AuthShell title="응원단에 합류해요!" subtitle="회원가입하고 나만의 응원 기록을 시작하세요">
      <form onSubmit={submit} className="space-y-3">
        <AuthField label="닉네임" value={nickname} onChange={setNickname} placeholder="응원단에서 사용할 닉네임" />
        <AuthField label="이메일" type="email" value={email} onChange={setEmail} placeholder="이메일을 입력하세요" autoComplete="email" />
        <AuthField label="비밀번호" type="password" value={pw} onChange={setPw} placeholder="비밀번호를 입력하세요 (8자 이상)" autoComplete="new-password" />
        <AuthField label="비밀번호 확인" type="password" value={pw2} onChange={setPw2} placeholder="비밀번호를 다시 입력하세요" autoComplete="new-password" />
        <button
          type="submit"
          disabled={signUpMutation.isPending}
          className="mt-1 w-full rounded-2xl bg-[var(--c-primary)] py-3.5 text-sm font-extrabold text-white transition-all hover:bg-[var(--c-primary-600)] disabled:opacity-60"
        >
          {signUpMutation.isPending ? "가입 중..." : "회원가입"}
        </button>
      </form>

      <Divider />
      <SocialButtons />

      <p className="mt-6 text-center text-sm text-[var(--c-ink-soft)]">
        이미 계정이 있으신가요?{" "}
        <Link to="/cheer/login" className="font-extrabold text-[var(--c-primary)]">
          로그인
        </Link>
      </p>
    </AuthShell>
  )
}
