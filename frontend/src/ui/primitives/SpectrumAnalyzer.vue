<!--
  SpectrumAnalyzer — FFT (1024 bins default) from an AnalyserNode, rendered
  as thin 2px vertical bars across a logarithmic 20Hz–20kHz axis. Colour
  gradient violeta → cian maps vertical magnitude. Optional peak hold.
-->
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    analyser: AnalyserNode | null
    width?: number
    height?: number
    minDb?: number
    maxDb?: number
    barWidth?: number
    barGap?: number
    peakHold?: boolean
    grid?: boolean
    label?: string
  }>(),
  {
    width: 640,
    height: 280,
    minDb: -90,
    maxDb: -10,
    barWidth: 2,
    barGap: 1,
    peakHold: true,
    grid: true,
  },
)

const canvasRef = ref<HTMLCanvasElement | null>(null)
let raf = 0
let holds: Float32Array | null = null
let freqBuffer: Float32Array | null = null

function draw() {
  const canvas = canvasRef.value
  const analyser = props.analyser
  if (!canvas) { raf = requestAnimationFrame(draw); return }
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const dpr = window.devicePixelRatio || 1
  const w = props.width
  const h = props.height
  if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
    canvas.width = w * dpr
    canvas.height = h * dpr
    canvas.style.width = w + 'px'
    canvas.style.height = h + 'px'
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, w, h)

  // Background.
  ctx.fillStyle = '#0e0e12'
  ctx.fillRect(0, 0, w, h)

  // Log-frequency grid.
  if (props.grid) {
    ctx.strokeStyle = 'rgba(255,255,255,0.04)'
    ctx.fillStyle = 'rgba(180,180,190,0.5)'
    ctx.font = '10px "JetBrains Mono", monospace'
    const nyquist = analyser ? (analyser.context.sampleRate / 2) : 24000
    const fMin = 20, fMax = Math.min(20000, nyquist)
    const marks = [100, 1000, 10000]
    for (const f of marks) {
      const x = Math.round(freqToX(f, fMin, fMax, w))
      ctx.beginPath()
      ctx.moveTo(x + 0.5, 0)
      ctx.lineTo(x + 0.5, h)
      ctx.stroke()
      const label = f >= 1000 ? `${f / 1000}k` : `${f}`
      ctx.fillText(label, x + 4, h - 6)
    }
  }

  if (!analyser) { raf = requestAnimationFrame(draw); return }

  if (!freqBuffer || freqBuffer.length !== analyser.frequencyBinCount) {
    freqBuffer = new Float32Array(analyser.frequencyBinCount)
    holds = new Float32Array(analyser.frequencyBinCount).fill(props.minDb)
  }
  analyser.getFloatFrequencyData(freqBuffer)

  const nyquist = analyser.context.sampleRate / 2
  const fMin = 20, fMax = Math.min(20000, nyquist)
  const totalBarWidth = props.barWidth + props.barGap
  const nBars = Math.floor(w / totalBarWidth)

  // Build gradient once per frame (cheap, needed because canvas reset).
  const grad = ctx.createLinearGradient(0, h, 0, 0)
  grad.addColorStop(0, '#7c5cff')
  grad.addColorStop(0.7, '#a88aff')
  grad.addColorStop(1, '#38bdf8')

  for (let i = 0; i < nBars; i++) {
    const x = i * totalBarWidth
    const ratio = i / (nBars - 1)
    // Log frequency for this bar.
    const f = fMin * Math.pow(fMax / fMin, ratio)
    const bin = Math.min(freqBuffer.length - 1, Math.floor((f / nyquist) * freqBuffer.length))
    const db = freqBuffer[bin]
    const v = Math.max(0, Math.min(1, (db - props.minDb) / (props.maxDb - props.minDb)))
    const barH = Math.round(v * (h - 4))

    ctx.fillStyle = grad
    ctx.fillRect(x, h - barH, props.barWidth, barH)

    if (props.peakHold && holds) {
      if (db > holds[bin]) holds[bin] = db
      else holds[bin] -= 0.2 // fast decay per frame
      const vh = Math.max(0, Math.min(1, (holds[bin] - props.minDb) / (props.maxDb - props.minDb)))
      const peakY = Math.round(h - vh * (h - 4))
      ctx.fillStyle = '#a88aff'
      ctx.fillRect(x, peakY - 1, props.barWidth, 1)
    }
  }

  raf = requestAnimationFrame(draw)
}

function freqToX(f: number, fMin: number, fMax: number, w: number) {
  const r = Math.log(f / fMin) / Math.log(fMax / fMin)
  return r * w
}

onMounted(() => { raf = requestAnimationFrame(draw) })
onBeforeUnmount(() => cancelAnimationFrame(raf))
watch(() => props.analyser, () => { holds = null; freqBuffer = null })
</script>

<template>
  <div class="spectrum">
    <div v-if="label" class="studio-label spectrum__label">{{ label }}</div>
    <canvas ref="canvasRef" class="spectrum__canvas" aria-hidden="true" />
  </div>
</template>

<style scoped>
.spectrum { display: flex; flex-direction: column; gap: 6px; }
.spectrum__canvas {
  display: block;
  width: 100%;
  border-radius: var(--radius-3);
  border: 1px solid var(--line);
  background: #0e0e12;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
}
</style>
