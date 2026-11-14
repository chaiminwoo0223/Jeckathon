import { cn } from "@/lib/utils"

// 뚜비 마스코트 — 실제 일러스트 PNG가 생기면 이 컴포넌트만 <img>로 교체.
// 지금은 브랜드 톤(흰 솜뭉치 + 선글라스 + 왕관 + 보라 머플러)에 맞춘 CSS/이모지 스탠드인.

const SIZES = {
  sm: { box: 44, face: 24, crown: 16 },
  md: { box: 72, face: 40, crown: 24 },
  lg: { box: 120, face: 64, crown: 40 },
  xl: { box: 168, face: 92, crown: 56 },
} as const

export function Mascot({
  size = "md",
  mood = "happy",
  float = false,
  flag = false,
  className,
}: {
  size?: keyof typeof SIZES
  mood?: "happy" | "sad" | "cool"
  float?: boolean
  flag?: boolean
  className?: string
}) {
  const s = SIZES[size]
  const face = mood === "sad" ? "🥺" : mood === "cool" ? "😎" : "😎"
  const body = mood === "sad" ? "#c9c4d6" : "#ffffff"

  return (
    <div
      className={cn("relative inline-grid place-items-center select-none", float && "cheer-float", className)}
      style={{ width: s.box, height: s.box }}
      aria-hidden
    >
      {/* crown */}
      <div
        className="absolute left-1/2 -translate-x-1/2 drop-shadow-sm"
        style={{ top: -s.crown * 0.55, fontSize: s.crown, filter: "saturate(1.2)" }}
      >
        👑
      </div>
      {/* body */}
      <div
        className="grid place-items-center rounded-full"
        style={{
          width: s.box,
          height: s.box,
          background: `radial-gradient(circle at 35% 30%, #ffffff, ${body})`,
          boxShadow:
            "inset 0 -8px 16px rgba(123,92,245,.12), 0 10px 24px -10px rgba(90,55,214,.45)",
          border: "3px solid #fff",
        }}
      >
        <span style={{ fontSize: s.face, transform: "translateY(2px)" }}>{face}</span>
      </div>
      {/* scarf */}
      <div
        className="absolute left-1/2 -translate-x-1/2 rounded-full"
        style={{
          bottom: -s.box * 0.02,
          width: s.box * 0.82,
          height: s.box * 0.18,
          background: "linear-gradient(90deg,#7b5cf5,#b794ff)",
        }}
      />
      {/* flag */}
      {flag && (
        <div className="absolute" style={{ right: -s.box * 0.22, top: -s.box * 0.1, fontSize: s.crown }}>
          🚩
        </div>
      )}
    </div>
  )
}
