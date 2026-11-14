import { useMutation, useQueryClient } from "@tanstack/react-query"
import {
  createFileRoute,
  Link,
  redirect,
  useNavigate,
} from "@tanstack/react-router"
import type { AxiosError } from "axios"
import { type FormEvent, useState } from "react"
import { toast } from "sonner"
import { AuthField } from "@/cheer/components/auth-field"
import { SocialButtons } from "@/cheer/components/social-buttons"
import { LoginService, MeService } from "@/client"
import { isLoggedIn } from "@/hooks/useAuth"
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
  const queryClient = useQueryClient()
  const [nickname, setNickname] = useState("")
  const [id, setId] = useState("")
  const [pw, setPw] = useState("")
  const [pw2, setPw2] = useState("")

  const signUpMutation = useMutation({
    mutationFn: async () => {
      const res = await LoginService.signup({
        body: { username: id.trim(), password: pw },
      })
      localStorage.setItem("access_token", res.data.access_token)
      // 가입 API는 닉네임을 받지 않아(아이디로 채워짐) 바로 프로필에 저장한다. 실패해도 가입은 끝났으니 진행
      await MeService.updateProfile({
        body: { nickname: nickname.trim() },
      }).catch(() => toast.error("닉네임은 마이페이지에서 다시 설정해주세요."))
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries()
      toast.success("회원가입 완료! 응원단에 오신 걸 환영해요")
      navigate({ to: "/cheer" })
    },
    onError: (err) => {
      const status = (err as AxiosError).response?.status
      toast.error(
        status === 409
          ? "이미 사용 중인 아이디예요."
          : status === 422
            ? "아이디는 영문·숫자·_ 4~20자로 입력해주세요."
            : "가입하지 못했어요. 잠시 후 다시 시도해주세요.",
      )
    },
  })

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!nickname.trim() || !id.trim() || !pw.trim()) {
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
    <AuthShell
      title="응원단에 합류해요!"
      subtitle="회원가입하고 나만의 응원 기록을 시작하세요"
    >
      <form onSubmit={submit} className="space-y-3">
        <AuthField
          label="닉네임"
          value={nickname}
          onChange={setNickname}
          placeholder="응원단에서 사용할 닉네임"
        />
        <AuthField
          label="아이디"
          value={id}
          onChange={setId}
          placeholder="영문·숫자·_ 4~20자"
          autoComplete="username"
        />
        <AuthField
          label="비밀번호"
          type="password"
          value={pw}
          onChange={setPw}
          placeholder="비밀번호를 입력하세요 (8자 이상)"
          autoComplete="new-password"
        />
        <AuthField
          label="비밀번호 확인"
          type="password"
          value={pw2}
          onChange={setPw2}
          placeholder="비밀번호를 다시 입력하세요"
          autoComplete="new-password"
        />
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
        <Link
          to="/cheer/login"
          className="font-extrabold text-[var(--c-primary)]"
        >
          로그인
        </Link>
      </p>
    </AuthShell>
  )
}
