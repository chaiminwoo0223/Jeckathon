// CHEER 101 사운드 — Web Audio API로 합성. 외부 파일 없이 오프라인·즉시 재생.
// 브라우저 자동재생 정책상 사용자 제스처(버튼 클릭) 이후에만 소리가 납니다.

let ctx: AudioContext | null = null

function ac(): AudioContext | null {
  if (typeof window === "undefined") return null
  const AC = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!AC) return null
  if (!ctx) ctx = new AC()
  if (ctx.state === "suspended") ctx.resume().catch(() => {})
  return ctx
}

function tone(
  freq: number,
  start: number,
  dur: number,
  type: OscillatorType = "triangle",
  gain = 0.2,
) {
  const c = ac()
  if (!c) return
  const o = c.createOscillator()
  const g = c.createGain()
  o.type = type
  o.frequency.value = freq
  o.connect(g)
  g.connect(c.destination)
  const t = c.currentTime + start
  g.gain.setValueAtTime(0.0001, t)
  g.gain.exponentialRampToValueAtTime(gain, t + 0.03)
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur)
  o.start(t)
  o.stop(t + dur + 0.03)
}

// 군중 함성 — 화이트노이즈 + 로우패스 스웰
function roar(start: number, dur: number, peak = 0.22) {
  const c = ac()
  if (!c) return
  const frames = Math.floor(c.sampleRate * dur)
  const buffer = c.createBuffer(1, frames, c.sampleRate)
  const data = buffer.getChannelData(0)
  for (let i = 0; i < frames; i++) data[i] = Math.random() * 2 - 1
  const src = c.createBufferSource()
  src.buffer = buffer
  const filter = c.createBiquadFilter()
  filter.type = "lowpass"
  filter.frequency.value = 1100
  const g = c.createGain()
  src.connect(filter)
  filter.connect(g)
  g.connect(c.destination)
  const t = c.currentTime + start
  g.gain.setValueAtTime(0.0001, t)
  g.gain.linearRampToValueAtTime(peak, t + dur * 0.4)
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur)
  src.start(t)
  src.stop(t + dur)
}

// 🎉 빵빠레 — 상승 아르페지오 + 팡파르 코드 + 군중 함성
export function playFanfare() {
  const brass: Array<[number, number]> = [
    [523.25, 0], // C5
    [659.25, 0.13], // E5
    [783.99, 0.26], // G5
    [1046.5, 0.42], // C6
  ]
  for (const [f, s] of brass) {
    tone(f, s, 0.55, "sawtooth", 0.16)
    tone(f / 2, s, 0.55, "triangle", 0.1)
  }
  // 피날레 코드 (C6 + E6 + G6)
  for (const f of [1046.5, 1318.51, 1567.98]) tone(f, 0.56, 1.0, "triangle", 0.13)
  roar(0.3, 1.4, 0.2)
}

// 📣 대결 시작 휘슬
export function playWhistle() {
  tone(2100, 0, 0.18, "square", 0.12)
  tone(2500, 0.12, 0.22, "square", 0.12)
}

// ⏱️ 카운트다운 틱
export function playTick(final = false) {
  tone(final ? 1320 : 880, 0, final ? 0.3 : 0.08, "square", 0.1)
}

// ✨ 가벼운 UI 팝
export function playPop() {
  tone(660, 0, 0.1, "triangle", 0.12)
  tone(990, 0.06, 0.12, "triangle", 0.1)
}
