import { useEffect, useRef } from "react"
import { ARENA_PLAY_RADIUS } from "../presence/types"

// 원형 경계 안으로 좌표 제한
export function clampToArena(x: number, z: number): { x: number; z: number } {
  const d = Math.hypot(x, z)
  if (d <= ARENA_PLAY_RADIUS) return { x, z }
  const s = ARENA_PLAY_RADIUS / d
  return { x: x * s, z: z * s }
}

export type MoveInput = { x: number; z: number } // 정규화된 이동 방향(-1..1)

// 키보드 입력을 ref로 수집. 조이스틱도 같은 ref에 값을 쓸 수 있다.
export function useKeyboardInput() {
  const input = useRef<MoveInput>({ x: 0, z: 0 })
  useEffect(() => {
    const keys = new Set<string>()
    const recompute = () => {
      let x = 0
      let z = 0
      if (keys.has("KeyW") || keys.has("ArrowUp")) z -= 1
      if (keys.has("KeyS") || keys.has("ArrowDown")) z += 1
      if (keys.has("KeyA") || keys.has("ArrowLeft")) x -= 1
      if (keys.has("KeyD") || keys.has("ArrowRight")) x += 1
      const len = Math.hypot(x, z) || 1
      input.current = { x: x / len, z: z / len }
    }
    // 채팅 입력창 등에 포커스가 있으면 이동키를 먹지 않는다.
    const isTyping = () => {
      const el = document.activeElement
      if (!el) return false
      const tag = el.tagName
      return (
        tag === "INPUT" ||
        tag === "TEXTAREA" ||
        (el as HTMLElement).isContentEditable
      )
    }
    const down = (e: KeyboardEvent) => {
      if (isTyping()) return
      if (
        e.code === "ArrowUp" ||
        e.code === "ArrowDown" ||
        e.code === "ArrowLeft" ||
        e.code === "ArrowRight"
      ) {
        e.preventDefault()
      }
      keys.add(e.code)
      recompute()
    }
    const up = (e: KeyboardEvent) => {
      keys.delete(e.code)
      recompute()
    }
    window.addEventListener("keydown", down)
    window.addEventListener("keyup", up)
    return () => {
      window.removeEventListener("keydown", down)
      window.removeEventListener("keyup", up)
    }
  }, [])
  return input
}
