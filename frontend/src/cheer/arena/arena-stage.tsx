import { Canvas, useFrame, useThree } from "@react-three/fiber"
import { ArrowLeft, MessageCircle, X } from "lucide-react"
import type { MutableRefObject } from "react"
import { useRef, useState } from "react"
import * as THREE from "three"
import { LiveChat } from "@/cheer/components/live-chat"
import { Joystick } from "./controls/joystick"
import {
  clampToArena,
  type MoveInput,
  useKeyboardInput,
} from "./controls/use-movement"
import type { ArenaTeam } from "./presence/types"
import { usePresence } from "./presence/use-presence"
import { Avatar } from "./scene/avatar"
import { Stadium } from "./scene/stadium"

const SPEED = 5 // m/s

function World({
  inputRef,
  myTeam,
  myNickname,
}: {
  inputRef: MutableRefObject<MoveInput>
  myTeam: ArenaTeam
  myNickname: string
}) {
  const { players, me, move } = usePresence(myNickname, myTeam)
  const pos = useRef({ x: me.x, z: me.z, rotation: me.rotation })
  const { camera } = useThree()
  const camTarget = useRef(new THREE.Vector3())
  const camDesired = useRef(new THREE.Vector3())

  useFrame((_, rawDt) => {
    const dt = Math.min(0.05, rawDt)
    const inp = inputRef.current
    if (inp.x !== 0 || inp.z !== 0) {
      const nx = pos.current.x + inp.x * SPEED * dt
      const nz = pos.current.z + inp.z * SPEED * dt
      const c = clampToArena(nx, nz)
      pos.current.x = c.x
      pos.current.z = c.z
      pos.current.rotation = Math.atan2(inp.x, inp.z)
      move({ x: c.x, z: c.z, rotation: pos.current.rotation })
    }

    // 3인칭 추적 카메라 (스타디움 조망 — 경기장 전체가 보이게 높고 멀게)
    camTarget.current.set(pos.current.x * 0.5, 3.5, pos.current.z * 0.5)
    camDesired.current.set(pos.current.x, 10, pos.current.z + 15)
    camera.position.lerp(camDesired.current, Math.min(1, dt * 3))
    camera.lookAt(camTarget.current)
  })

  return (
    <>
      <Stadium />
      {players.map((p) => (
        <Avatar key={p.id} player={p} />
      ))}
    </>
  )
}

export function ArenaStage({
  onExit,
  myTeam,
  myNickname = "나",
}: {
  onExit: () => void
  myTeam: ArenaTeam
  myNickname?: string
}) {
  const inputRef = useKeyboardInput()
  const [chatOpen, setChatOpen] = useState(true)
  return (
    <div className="cheer-reveal fixed inset-0 z-40 bg-gradient-to-b from-[#bfe3ff] to-[#7fc3f0]">
      <Canvas shadows camera={{ position: [0, 10, 21], fov: 52 }}>
        <fog attach="fog" args={["#bfe3ff", 40, 95]} />
        <World inputRef={inputRef} myTeam={myTeam} myNickname={myNickname} />
      </Canvas>

      {/* HUD */}
      <button
        type="button"
        onClick={onExit}
        className="absolute right-4 top-4 inline-flex items-center gap-1.5 rounded-full bg-white/90 px-4 py-2 text-sm font-extrabold text-[var(--c-ink)] shadow-md"
      >
        <ArrowLeft size={16} /> 나가기
      </button>
      <div className="pointer-events-none absolute left-1/2 top-4 -translate-x-1/2 rounded-full bg-black/40 px-4 py-1.5 text-center text-xs font-bold text-white backdrop-blur-sm">
        WASD·방향키(모바일은 조이스틱)로 이동 · 팀 유니폼 입은 팬들과 함께
        응원하세요
      </div>
      {/* 메타버스 채팅 */}
      {chatOpen ? (
        <div className="absolute bottom-4 right-4 w-[300px] max-w-[calc(100vw-2rem)]">
          <div className="relative">
            <button
              type="button"
              onClick={() => setChatOpen(false)}
              className="absolute -right-2 -top-2 z-10 grid size-7 place-items-center rounded-full bg-[var(--c-ink)] text-white shadow-md"
              aria-label="채팅 닫기"
            >
              <X size={14} />
            </button>
            <LiveChat heightClass="h-[200px]" />
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setChatOpen(true)}
          className="absolute bottom-4 right-4 inline-flex items-center gap-1.5 rounded-full bg-[var(--c-primary)] px-4 py-2.5 text-sm font-extrabold text-white shadow-md"
        >
          <MessageCircle size={16} /> 응원 채팅
        </button>
      )}

      <Joystick inputRef={inputRef} />
    </div>
  )
}
