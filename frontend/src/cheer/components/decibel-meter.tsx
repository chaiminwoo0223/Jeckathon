import { cn } from "@/lib/utils"

// 반원형 데시벨 게이지 + 이퀄라이저 바
export function DecibelMeter({
  db,
  active,
  label,
  size = 260,
}: {
  db: number
  active: boolean
  label?: string
  size?: number
}) {
  const min = 40
  const max = 120
  const ratio = Math.min(1, Math.max(0, (db - min) / (max - min)))
  const r = size / 2 - 14
  const circ = Math.PI * r // 반원 길이
  const dash = circ

  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size * 0.62 }}>
      <svg width={size} height={size * 0.62} viewBox={`0 0 ${size} ${size * 0.62}`} className="overflow-visible" role="img" aria-label={`데시벨 ${db.toFixed(0)}`}>
        <title>데시벨 게이지</title>
        <defs>
          <linearGradient id="dbgrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#7b5cf5" />
            <stop offset="55%" stopColor="#b794ff" />
            <stop offset="100%" stopColor="#f06ba8" />
          </linearGradient>
        </defs>
        {/* track */}
        <path
          d={`M 14 ${size * 0.62 - 10} A ${r} ${r} 0 0 1 ${size - 14} ${size * 0.62 - 10}`}
          fill="none"
          stroke="var(--c-primary-50)"
          strokeWidth={14}
          strokeLinecap="round"
        />
        {/* value */}
        <path
          d={`M 14 ${size * 0.62 - 10} A ${r} ${r} 0 0 1 ${size - 14} ${size * 0.62 - 10}`}
          fill="none"
          stroke="url(#dbgrad)"
          strokeWidth={14}
          strokeLinecap="round"
          strokeDasharray={dash}
          strokeDashoffset={dash * (1 - ratio)}
          style={{ transition: "stroke-dashoffset 0.12s linear" }}
        />
      </svg>

      <div className="absolute inset-0 grid place-content-center text-center" style={{ top: size * 0.08 }}>
        {/* equalizer */}
        <div className="mb-1 flex h-7 items-end justify-center gap-[3px]">
          {Array.from({ length: 13 }).map((_, i) => (
            <span
              key={i}
              className={cn("w-[4px] rounded-full", active ? "cheer-eq-bar" : "")}
              style={{
                height: "100%",
                backgroundColor: i < ratio * 13 ? "var(--c-primary)" : "var(--c-primary-100)",
                animationDelay: `${i * 0.06}s`,
                opacity: active ? 1 : 0.55,
              }}
            />
          ))}
        </div>
        <div className="text-[44px] font-black leading-none tracking-tight text-[var(--c-ink)]">
          {db.toFixed(1)}
          <span className="ml-1 text-xl text-[var(--c-primary)]">dB</span>
        </div>
        {label && <div className="mt-1 text-sm font-semibold text-[var(--c-ink-soft)]">{label}</div>}
      </div>
    </div>
  )
}
