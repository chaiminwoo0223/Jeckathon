import { useCallback, useEffect, useRef, useState } from "react"

export type MicStatus = "idle" | "requesting" | "live" | "simulated" | "denied"

// 실시간 마이크 음량 → 데시벨(dB) 근사치.
// 마이크 권한이 있으면 Web Audio API로 실제 측정, 없으면 시뮬레이션으로 데모 유지.
export function useDecibel(active: boolean) {
  const [db, setDb] = useState(0)
  const [peak, setPeak] = useState(0)
  const [status, setStatus] = useState<MicStatus>("idle")

  const rafRef = useRef<number | null>(null)
  const ctxRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const peakRef = useRef(0)
  const simPhaseRef = useRef(0)

  const cleanup = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    for (const t of streamRef.current?.getTracks() ?? []) t.stop()
    streamRef.current = null
    ctxRef.current?.close().catch(() => {})
    ctxRef.current = null
    analyserRef.current = null
  }, [])

  const reset = useCallback(() => {
    peakRef.current = 0
    setPeak(0)
    setDb(0)
  }, [])

  useEffect(() => {
    if (!active) {
      cleanup()
      setStatus("idle")
      setDb(0)
      return
    }

    let cancelled = false

    const toDb = (level0to1: number) => {
      // 40dB(조용) ~ 120dB(함성) 사이로 맵핑, 소리 지르면 쉽게 100 넘도록 가중
      const v = Math.min(1, level0to1 * 1.6)
      return Math.round((40 + v * 80) * 10) / 10
    }

    const track = (value: number) => {
      setDb(value)
      if (value > peakRef.current) {
        peakRef.current = value
        setPeak(value)
      }
    }

    const runSimulated = () => {
      setStatus("simulated")
      const tick = () => {
        simPhaseRef.current += 0.12
        const base = 78 + Math.sin(simPhaseRef.current) * 10
        const spike = Math.random() < 0.18 ? Math.random() * 24 : Math.random() * 6
        track(Math.round(Math.min(120, base + spike) * 10) / 10)
        rafRef.current = requestAnimationFrame(tick)
      }
      tick()
    }

    const runMic = async () => {
      setStatus("requesting")
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        if (cancelled) {
          for (const t of stream.getTracks()) t.stop()
          return
        }
        streamRef.current = stream
        const AC = window.AudioContext || (window as any).webkitAudioContext
        const ctx = new AC()
        ctxRef.current = ctx
        const src = ctx.createMediaStreamSource(stream)
        const analyser = ctx.createAnalyser()
        analyser.fftSize = 512
        src.connect(analyser)
        analyserRef.current = analyser
        const data = new Uint8Array(analyser.frequencyBinCount)
        setStatus("live")

        const tick = () => {
          analyser.getByteFrequencyData(data)
          let sum = 0
          for (const x of data) sum += x
          const avg = sum / data.length / 255 // 0~1
          track(toDb(avg))
          rafRef.current = requestAnimationFrame(tick)
        }
        tick()
      } catch {
        if (!cancelled) {
          setStatus("denied")
          runSimulated()
        }
      }
    }

    if (typeof navigator.mediaDevices?.getUserMedia === "function") {
      runMic()
    } else {
      runSimulated()
    }

    return () => {
      cancelled = true
      cleanup()
    }
  }, [active, cleanup])

  return { db, peak, status, reset }
}
