import { Html } from "@react-three/drei"
import type { Player } from "../presence/types"
import { NameTag } from "./speech-bubble"

const SKIN = "#ffd9ad"

export function Avatar({ player }: { player: Player }) {
  const { x, z, rotation, team, isMe } = player
  return (
    <group position={[x, 0, z]} rotation={[0, rotation, 0]}>
      {/* 몸통(팀 유니폼 색) */}
      <mesh position={[0, 0.7, 0]} castShadow>
        <capsuleGeometry args={[0.45, 0.7, 6, 12]} />
        <meshStandardMaterial color={team.color} />
      </mesh>

      {/* 팔 (어깨 피벗에서 몸통을 따라 아래로) */}
      {([-1, 1] as const).map((side) => (
        <group
          key={side}
          position={[side * 0.38, 0.98, 0]}
          rotation={[0, 0, side * -0.14]}
        >
          {/* 어깨 이음새 */}
          <mesh castShadow>
            <sphereGeometry args={[0.15, 12, 12]} />
            <meshStandardMaterial color={team.color} />
          </mesh>
          {/* 윗팔~아래팔(소매) */}
          <mesh position={[0, -0.32, 0]} castShadow>
            <capsuleGeometry args={[0.13, 0.42, 6, 10]} />
            <meshStandardMaterial color={team.color} />
          </mesh>
          {/* 손 */}
          <mesh position={[0, -0.66, 0]}>
            <sphereGeometry args={[0.12, 10, 10]} />
            <meshStandardMaterial color={SKIN} />
          </mesh>
        </group>
      ))}

      {/* 머리 */}
      <mesh position={[0, 1.55, 0]} castShadow>
        <sphereGeometry args={[0.38, 20, 20]} />
        <meshStandardMaterial color={SKIN} />
      </mesh>

      {/* 얼굴: 눈 (흰자 + 눈동자) */}
      <group position={[0, 1.6, 0.3]}>
        <mesh position={[-0.13, 0.03, 0.03]}>
          <sphereGeometry args={[0.075, 12, 12]} />
          <meshStandardMaterial color="#ffffff" />
        </mesh>
        <mesh position={[0.13, 0.03, 0.03]}>
          <sphereGeometry args={[0.075, 12, 12]} />
          <meshStandardMaterial color="#ffffff" />
        </mesh>
        <mesh position={[-0.13, 0.03, 0.09]}>
          <sphereGeometry args={[0.035, 10, 10]} />
          <meshStandardMaterial color="#20232a" />
        </mesh>
        <mesh position={[0.13, 0.03, 0.09]}>
          <sphereGeometry args={[0.035, 10, 10]} />
          <meshStandardMaterial color="#20232a" />
        </mesh>
      </group>

      {/* 코 */}
      <mesh position={[0, 1.55, 0.37]}>
        <sphereGeometry args={[0.05, 10, 10]} />
        <meshStandardMaterial color="#f0b78a" />
      </mesh>

      {/* 입 */}
      <mesh position={[0, 1.44, 0.34]} rotation={[0, 0, 0]}>
        <boxGeometry args={[0.16, 0.035, 0.03]} />
        <meshStandardMaterial color="#c0392b" />
      </mesh>

      {/* 가슴 팀명 라벨 (한글 렌더를 위해 Html 사용, 카메라를 향함) */}
      <Html
        position={[0, 0.85, 0]}
        center
        distanceFactor={11}
        zIndexRange={[5, 0]}
        pointerEvents="none"
      >
        <div
          style={{
            background: "rgba(255,255,255,.92)",
            color: team.color,
            borderRadius: 6,
            padding: "1px 6px",
            fontSize: 10,
            fontWeight: 800,
            whiteSpace: "nowrap",
            border: `1.5px solid ${team.color}`,
            userSelect: "none",
          }}
        >
          {team.name}
        </div>
      </Html>

      {/* 내 아바타 발밑 하이라이트 */}
      {isMe && (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
          <ringGeometry args={[0.55, 0.72, 24]} />
          <meshStandardMaterial color="#f6b93b" />
        </mesh>
      )}

      <NameTag nickname={player.nickname} message={player.message} />
    </group>
  )
}
