import { Eye, EyeOff } from "lucide-react"
import { useState } from "react"

export function AuthField({
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  autoComplete,
}: {
  label: string
  type?: "text" | "password"
  value: string
  onChange: (v: string) => void
  placeholder?: string
  autoComplete?: string
}) {
  const [show, setShow] = useState(false)
  const isPw = type === "password"
  const inputType = isPw ? (show ? "text" : "password") : type

  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-bold text-[var(--c-ink-soft)]">{label}</span>
      <div className="relative">
        <input
          type={inputType}
          value={value}
          autoComplete={autoComplete}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className="w-full rounded-2xl border bg-[var(--c-surface-2)] px-4 py-3 text-sm outline-none transition-all placeholder:text-[var(--c-muted)] focus:border-[var(--c-primary)] focus:ring-2 focus:ring-[var(--c-primary-100)]"
          style={{ borderColor: "var(--c-line)" }}
        />
        {isPw && (
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--c-muted)] hover:text-[var(--c-ink-soft)]"
            aria-label={show ? "비밀번호 숨기기" : "비밀번호 표시"}
          >
            {show ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        )}
      </div>
    </label>
  )
}
