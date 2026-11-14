// SNS 공유용 카드 이미지 생성 + 다운로드.
// 외부 라이브러리 없이 Canvas로 직접 그린다(폰트/CORS 이슈 없이 데모에서 안정적).
// 실제 일러스트/브랜드 폰트가 생기면 drawMascot / FONT 만 교체하면 됨.

export interface ShareCardData {
  nickname: string
  fairyTitle: string // 예: "승리요정"
  winRateText: string // 예: "68%"
  totalMatches: number
  favoriteTeam: string
  stats: { win: number; draw: number; lose: number }
}

const W = 1080
const H = 1350
const FONT = `-apple-system, "Pretendard", "Apple SD Gothic Neo", "Noto Sans KR", system-ui, sans-serif`

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, r)
}

function drawMascot(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  r: number,
) {
  // 흰 몸통
  ctx.save()
  ctx.beginPath()
  ctx.arc(cx, cy, r, 0, Math.PI * 2)
  const g = ctx.createRadialGradient(
    cx - r * 0.3,
    cy - r * 0.3,
    r * 0.2,
    cx,
    cy,
    r,
  )
  g.addColorStop(0, "#ffffff")
  g.addColorStop(1, "#efeaff")
  ctx.fillStyle = g
  ctx.shadowColor = "rgba(40,20,90,0.35)"
  ctx.shadowBlur = 40
  ctx.shadowOffsetY = 18
  ctx.fill()
  ctx.restore()

  // 머플러
  ctx.save()
  ctx.fillStyle = "#8a6bff"
  roundRect(ctx, cx - r * 0.72, cy + r * 0.72, r * 1.44, r * 0.34, r * 0.17)
  ctx.fill()
  ctx.restore()

  // 얼굴(선글라스) + 왕관
  ctx.textAlign = "center"
  ctx.textBaseline = "middle"
  ctx.font = `${r * 1.1}px ${FONT}`
  ctx.fillText("😎", cx, cy + r * 0.08)
  ctx.font = `${r * 0.78}px ${FONT}`
  ctx.fillText("👑", cx, cy - r * 0.92)
}

function drawShareCard(ctx: CanvasRenderingContext2D, data: ShareCardData) {
  // 배경 그라데이션
  const bg = ctx.createLinearGradient(0, 0, W, H)
  bg.addColorStop(0, "#7b5cf5")
  bg.addColorStop(1, "#5a37d6")
  ctx.fillStyle = bg
  ctx.fillRect(0, 0, W, H)

  // 우상단 하이라이트
  const hl = ctx.createRadialGradient(
    W * 0.85,
    H * 0.12,
    0,
    W * 0.85,
    H * 0.12,
    520,
  )
  hl.addColorStop(0, "rgba(255,255,255,0.28)")
  hl.addColorStop(1, "rgba(255,255,255,0)")
  ctx.fillStyle = hl
  ctx.fillRect(0, 0, W, H)

  // 장식 원
  ctx.fillStyle = "rgba(255,255,255,0.06)"
  ctx.beginPath()
  ctx.arc(W * 0.12, H * 0.9, 220, 0, Math.PI * 2)
  ctx.fill()

  ctx.textAlign = "center"

  // 로고
  ctx.fillStyle = "rgba(255,255,255,0.9)"
  ctx.font = `800 46px ${FONT}`
  ctx.fillText("📣 CHEER 101", W / 2, 110)

  // 라벨
  ctx.fillStyle = "rgba(255,255,255,0.78)"
  ctx.font = `700 38px ${FONT}`
  ctx.fillText("나의 응원 기록", W / 2, 205)

  // 마스코트
  drawMascot(ctx, W / 2, 400, 120)

  // 승률
  ctx.fillStyle = "#ffe08a"
  ctx.font = `900 150px ${FONT}`
  ctx.fillText(`승률 ${data.winRateText}`, W / 2, 660)

  // 응원 경기 수
  ctx.fillStyle = "rgba(255,255,255,0.82)"
  ctx.font = `600 44px ${FONT}`
  ctx.fillText(`${data.totalMatches}경기 응원`, W / 2, 740)

  // 닉네임 / 요정
  ctx.fillStyle = "#ffffff"
  ctx.font = `900 64px ${FONT}`
  ctx.fillText(`👑 ${data.fairyTitle} ${data.nickname}`, W / 2, 860)

  // 최애팀 칩
  const chipText = `⭐ 최애팀 ${data.favoriteTeam}`
  ctx.font = `700 38px ${FONT}`
  const chipW = ctx.measureText(chipText).width + 72
  const chipH = 74
  const chipX = (W - chipW) / 2
  const chipY = 910
  ctx.fillStyle = "rgba(255,255,255,0.18)"
  roundRect(ctx, chipX, chipY, chipW, chipH, chipH / 2)
  ctx.fill()
  ctx.fillStyle = "#ffffff"
  ctx.textBaseline = "middle"
  ctx.fillText(chipText, W / 2, chipY + chipH / 2 + 2)
  ctx.textBaseline = "alphabetic"

  // 시즌 전적 박스
  const boxY = 1070
  const boxH = 150
  const boxX = 120
  const boxW = W - boxX * 2
  ctx.fillStyle = "rgba(255,255,255,0.14)"
  roundRect(ctx, boxX, boxY, boxW, boxH, 36)
  ctx.fill()

  const cells: Array<[string, number, string]> = [
    ["승", data.stats.win, "#8affcf"],
    ["무", data.stats.draw, "#e6e1ff"],
    ["패", data.stats.lose, "#ff9ec8"],
  ]
  const cellW = boxW / 3
  cells.forEach(([label, value, color], i) => {
    const cx = boxX + cellW * i + cellW / 2
    ctx.fillStyle = "rgba(255,255,255,0.75)"
    ctx.font = `700 36px ${FONT}`
    ctx.fillText(label, cx, boxY + 60)
    ctx.fillStyle = color
    ctx.font = `900 60px ${FONT}`
    ctx.fillText(String(value), cx, boxY + 120)
    if (i < cells.length - 1) {
      ctx.fillStyle = "rgba(255,255,255,0.2)"
      ctx.fillRect(boxX + cellW * (i + 1) - 1, boxY + 30, 2, boxH - 60)
    }
  })

  // 푸터
  ctx.fillStyle = "rgba(255,255,255,0.6)"
  ctx.font = `600 32px ${FONT}`
  ctx.fillText("cheer101.infoedu.co.kr", W / 2, 1290)
}

// 공유 카드를 PNG로 생성해 다운로드. 성공 시 resolve.
export function downloadShareCard(data: ShareCardData): Promise<void> {
  return new Promise((resolve, reject) => {
    const canvas = document.createElement("canvas")
    canvas.width = W
    canvas.height = H
    const ctx = canvas.getContext("2d")
    if (!ctx) {
      reject(new Error("canvas context를 만들 수 없어요"))
      return
    }
    drawShareCard(ctx, data)
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error("이미지 생성에 실패했어요"))
        return
      }
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `cheer101-${data.nickname}-응원기록.png`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      resolve()
    }, "image/png")
  })
}
