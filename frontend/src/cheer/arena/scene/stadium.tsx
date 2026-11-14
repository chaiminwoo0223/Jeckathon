import { Instance, Instances } from "@react-three/drei"
import { useMemo } from "react"
import { ARENA_RADIUS } from "../presence/types"

const CROWD_COLORS = [
  "#ef4444",
  "#3b82f6",
  "#f59e0b",
  "#10b981",
  "#ffffff",
  "#a855f7",
  "#ec4899",
  "#132257",
  "#ffd9ad",
  "#eab308",
]

// 결정적 의사난수(시드) — 렌더마다 관중이 바뀌지 않게.
function makeRand(seed: number) {
  let s = seed
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296
    return s / 4294967296
  }
}

type Spectator = { pos: [number, number, number]; color: string }

function buildCrowd(): Spectator[] {
  const rand = makeRand(20261114)
  const arr: Spectator[] = []
  const tiers = 6
  for (let t = 0; t < tiers; t++) {
    const radius = ARENA_RADIUS + 2.2 + t * 1.0
    const y = 1.3 + t * 0.78
    const count = Math.max(24, Math.floor((2 * Math.PI * radius) / 1.05))
    for (let i = 0; i < count; i++) {
      const a = (i / count) * Math.PI * 2 + (t % 2) * 0.06
      arr.push({
        pos: [Math.cos(a) * radius, y, Math.sin(a) * radius],
        color: CROWD_COLORS[Math.floor(rand() * CROWD_COLORS.length)],
      })
    }
  }
  return arr
}

function Crowd() {
  const crowd = useMemo(buildCrowd, [])
  return (
    <Instances limit={crowd.length} range={crowd.length} castShadow>
      <boxGeometry args={[0.42, 0.72, 0.42]} />
      <meshStandardMaterial />
      {crowd.map((c, i) => (
        <Instance key={i} position={c.pos} color={c.color} />
      ))}
    </Instances>
  )
}

export function Stadium() {
  const floodlights = useMemo(() => {
    const n = 8
    return Array.from({ length: n }, (_, i) => {
      const a = (i / n) * Math.PI * 2
      const r = ARENA_RADIUS + 8.5
      return [Math.cos(a) * r, 0, Math.sin(a) * r] as [number, number, number]
    })
  }, [])

  return (
    <group>
      {/* 조명 */}
      <ambientLight intensity={0.95} />
      <directionalLight position={[14, 26, 10]} intensity={1.1} castShadow />
      <hemisphereLight args={["#eaf4ff", "#2f4f22", 0.6]} />

      {/* 잔디 원형 바닥 */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <circleGeometry args={[ARENA_RADIUS, 64]} />
        <meshStandardMaterial color="#3f8f3a" />
      </mesh>

      {/* 중앙 서클 라인 */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <ringGeometry args={[2.4, 2.6, 48]} />
        <meshStandardMaterial color="#eafff0" />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.011, 0]}>
        <circleGeometry args={[0.25, 24]} />
        <meshStandardMaterial color="#eafff0" />
      </mesh>
      {/* 외곽 터치라인 */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <ringGeometry args={[ARENA_RADIUS - 1.2, ARENA_RADIUS - 1.0, 64]} />
        <meshStandardMaterial color="#eafff0" />
      </mesh>

      {/* 관중석 보울(안쪽 낮고 바깥 높은 경사면) */}
      <mesh position={[0, 3, 0]}>
        <cylinderGeometry
          args={[ARENA_RADIUS + 9, ARENA_RADIUS + 1, 6, 64, 1, true]}
        />
        <meshStandardMaterial color="#9aa3b2" side={2} />
      </mesh>

      {/* 관중 */}
      <Crowd />

      {/* 지붕 링 */}
      <mesh position={[0, 9.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <torusGeometry args={[ARENA_RADIUS + 9, 0.7, 10, 64]} />
        <meshStandardMaterial color="#20262f" metalness={0.4} roughness={0.5} />
      </mesh>
      {/* 지붕 캐노피(안쪽에서 보이는 밝은 천장) */}
      <mesh position={[0, 9, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[ARENA_RADIUS + 2, ARENA_RADIUS + 9, 64]} />
        <meshStandardMaterial color="#e7ecf3" side={2} />
      </mesh>

      {/* 조명탑 */}
      {floodlights.map((p, i) => (
        <group key={i} position={p}>
          <mesh position={[0, 5, 0]}>
            <cylinderGeometry args={[0.25, 0.3, 10, 8]} />
            <meshStandardMaterial color="#39414d" />
          </mesh>
          <mesh position={[0, 10.3, 0]}>
            <boxGeometry args={[1.8, 0.8, 0.3]} />
            <meshStandardMaterial
              color="#fffbe6"
              emissive="#fff3b0"
              emissiveIntensity={1.2}
            />
          </mesh>
        </group>
      ))}
    </group>
  )
}
