import { useEffect, useRef, useState } from "react"

// 숫자가 0 → target 으로 차오르는 연출 (data 연동 전 데모 임팩트용)
export function useCountUp(target: number, durationMs = 1200, run = true) {
  const [value, setValue] = useState(0)
  const startRef = useRef<number | null>(null)
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    if (!run) {
      setValue(target)
      return
    }
    startRef.current = null
    const ease = (t: number) => 1 - (1 - t) ** 3 // easeOutCubic
    const step = (ts: number) => {
      if (startRef.current === null) startRef.current = ts
      const p = Math.min(1, (ts - startRef.current) / durationMs)
      setValue(target * ease(p))
      if (p < 1) rafRef.current = requestAnimationFrame(step)
    }
    rafRef.current = requestAnimationFrame(step)
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [target, durationMs, run])

  return value
}
