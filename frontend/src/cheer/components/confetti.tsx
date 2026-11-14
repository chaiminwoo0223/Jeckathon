// 가벼운 CSS 컨페티 + 스트리머 (대결 종료/승리 연출)
const COLORS = ["#7b5cf5", "#b794ff", "#f6b93b", "#f06ba8", "#22b07d", "#ffffff", "#ffd36b"]

export function Confetti({ count = 60, streamers = true }: { count?: number; streamers?: boolean }) {
  return (
    <div className="pointer-events-none absolute inset-0 z-20 overflow-hidden" aria-hidden>
      {Array.from({ length: count }).map((_, i) => {
        const left = (i * 97) % 100
        const delay = (i % 12) * 0.12
        const dur = 2 + ((i * 13) % 22) / 10
        const size = 6 + (i % 4) * 3
        const color = COLORS[i % COLORS.length]
        const shape = i % 3
        return (
          <span
            key={`c${i}`}
            style={{
              position: "absolute",
              left: `${left}%`,
              top: "-8vh",
              width: shape === 1 ? size * 0.5 : size,
              height: shape === 1 ? size : size * 0.5,
              background: color,
              borderRadius: shape === 0 ? "50%" : 2,
              animation: `cheer-confetti ${dur}s ${delay}s ease-in forwards`,
            }}
          />
        )
      })}
      {streamers &&
        Array.from({ length: Math.round(count / 4) }).map((_, i) => {
          const left = (i * 53 + 7) % 100
          const delay = (i % 8) * 0.18
          const dur = 2.6 + ((i * 7) % 16) / 10
          const color = COLORS[i % COLORS.length]
          return (
            <span
              key={`s${i}`}
              style={{
                position: "absolute",
                left: `${left}%`,
                top: "-12vh",
                width: 4,
                height: 26,
                background: `linear-gradient(${color}, transparent)`,
                borderRadius: 4,
                animation: `cheer-streamer ${dur}s ${delay}s linear forwards`,
              }}
            />
          )
        })}
    </div>
  )
}
