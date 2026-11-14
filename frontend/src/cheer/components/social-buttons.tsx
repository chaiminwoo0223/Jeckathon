import { Mail } from "lucide-react"
import { FcGoogle } from "react-icons/fc"
import { RiKakaoTalkFill } from "react-icons/ri"
import { toast } from "sonner"

// OAuth 미지원 — 버튼만 노출하고 클릭 시 안내 토스트.
const notSupported = () => toast("아직 지원하지 않는 기능입니다.")

export function SocialButtons() {
  return (
    <div className="space-y-2.5">
      <button
        type="button"
        onClick={notSupported}
        className="flex w-full items-center justify-center gap-2.5 rounded-2xl border bg-[var(--c-surface)] py-3 text-sm font-bold text-[var(--c-ink)] transition-all hover:bg-[var(--c-surface-2)]"
        style={{ borderColor: "var(--c-line)" }}
      >
        <FcGoogle size={20} /> Google로 계속하기
      </button>
      <button
        type="button"
        onClick={notSupported}
        className="flex w-full items-center justify-center gap-2.5 rounded-2xl py-3 text-sm font-bold text-[#191600] transition-all hover:brightness-95"
        style={{ background: "#FEE500" }}
      >
        <RiKakaoTalkFill size={20} /> 카카오로 계속하기
      </button>
      <button
        type="button"
        onClick={notSupported}
        className="flex w-full items-center justify-center gap-2.5 rounded-2xl border py-3 text-sm font-bold text-[var(--c-ink-soft)] transition-all hover:bg-[var(--c-surface-2)]"
        style={{ borderColor: "var(--c-line)" }}
      >
        <Mail size={18} /> 이메일로 계속하기
      </button>
    </div>
  )
}
