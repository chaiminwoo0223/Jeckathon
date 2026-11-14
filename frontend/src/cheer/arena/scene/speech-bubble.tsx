import { Html } from "@react-three/drei"

export function NameTag({
  nickname,
  message,
}: {
  nickname: string
  message?: string
}) {
  return (
    <Html
      position={[0, 2.4, 0]}
      center
      distanceFactor={14}
      zIndexRange={[10, 0]}
      pointerEvents="none"
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 4,
          pointerEvents: "none",
          userSelect: "none",
        }}
      >
        {message && (
          <div
            style={{
              background: "#fff",
              color: "#111827",
              borderRadius: 14,
              padding: "4px 10px",
              fontSize: 13,
              fontWeight: 700,
              boxShadow: "0 4px 12px rgba(0,0,0,.18)",
              whiteSpace: "nowrap",
            }}
          >
            {message}
          </div>
        )}
        <div
          style={{
            background: "rgba(17,24,39,.78)",
            color: "#fff",
            borderRadius: 10,
            padding: "2px 8px",
            fontSize: 11,
            fontWeight: 700,
            whiteSpace: "nowrap",
          }}
        >
          {nickname}
        </div>
      </div>
    </Html>
  )
}
