import type { MutableRefObject } from "react"
import { useRef, useState } from "react"
import type { MoveInput } from "./use-movement"

const R = 52 // 베이스 반경(px)

export function Joystick({
  inputRef,
}: {
  inputRef: MutableRefObject<MoveInput>
}) {
  const base = useRef<HTMLDivElement>(null)
  const [knob, setKnob] = useState({ x: 0, y: 0 })
  const active = useRef(false)

  const set = (clientX: number, clientY: number) => {
    const el = base.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    let dx = clientX - cx
    let dy = clientY - cy
    const d = Math.hypot(dx, dy)
    if (d > R) {
      dx = (dx / d) * R
      dy = (dy / d) * R
    }
    setKnob({ x: dx, y: dy })
    inputRef.current = { x: dx / R, z: dy / R }
  }

  const reset = () => {
    active.current = false
    setKnob({ x: 0, y: 0 })
    inputRef.current = { x: 0, z: 0 }
  }

  return (
    <div
      ref={base}
      className="absolute bottom-7 left-7 size-[112px] touch-none rounded-full bg-black/20 backdrop-blur-sm md:hidden"
      onTouchStart={(e) => {
        active.current = true
        set(e.touches[0].clientX, e.touches[0].clientY)
      }}
      onTouchMove={(e) => {
        if (active.current) set(e.touches[0].clientX, e.touches[0].clientY)
      }}
      onTouchEnd={reset}
      onTouchCancel={reset}
    >
      <div
        className="absolute left-1/2 top-1/2 size-12 rounded-full bg-white/80 shadow"
        style={{
          transform: `translate(calc(-50% + ${knob.x}px), calc(-50% + ${knob.y}px))`,
        }}
      />
    </div>
  )
}
