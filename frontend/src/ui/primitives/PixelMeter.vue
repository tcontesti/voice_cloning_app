<!--
  PixelMeter — hardware-style level meter.
  Horizontal or vertical, N columns × M rows of square pixels. Each pixel
  lights up with a colour that depends on its position inside the meter:
  green → amber → red. Peak hold line decays 12 dB/s (spec).

  Input: `rms` and `peak` as dBFS values (negative, -60..+3). Update via
  external rAF loop (e.g. a useMeter composable); the component also exposes
  a demo mode that animates synthetic values when no input is provided.
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

type Orientation = 'horizontal' | 'vertical'

const props = withDefaults(
  defineProps<{
    rms?: number           // dBFS, negative
    peak?: number          // dBFS, negative
    orientation?: Orientation
    cells?: number         // cells along the axis (default 32)
    rows?: number          // rows across the axis (default 6)
    minDb?: number
    maxDb?: number
    peakDecayDbPerSec?: number
    label?: string
    width?: number         // css px for the drawing area
    height?: number
    demo?: boolean
  }>(),
  {
    rms: -60,
    peak: -60,
    orientation: 'horizontal',
    cells: 32,
    rows: 6,
    minDb: -60,
    maxDb: 3,
    peakDecayDbPerSec: 12,
    width: 320,
    height: 56,
    demo: false,
  },
)

const canvasRef = ref<HTMLCanvasElement | null>(null)

// Hold state (dB) with decay; drops peakDecayDbPerSec dB per second when the
// incoming peak is lower than the held value.
let peakHoldDb = props.peak
let lastTs = 0
let raf = 0
let demoPhase = 0

const rmsDb = ref(props.rms)
const displayPeakDb = ref(props.peak)

watch(() => props.rms, (v) => { rmsDb.value = v })
watch(() => props.peak, (v) => {
  // Instant attack on peak, hold line uses decay.
  displayPeakDb.value = v
  if (v > peakHoldDb) peakHoldDb = v
})

function dbToRatio(db: number) {
  const range = props.maxDb - props.minDb
  return Math.max(0, Math.min(1, (db - props.minDb) / range))
}

// Cell colour: uses a non-linear split (70/20/10) as per spec.
function cellColour(axisRatio: number, active: boolean) {
  if (!active) return '#1a1a22' /* --meter-off */
  if (axisRatio < 0.7) return '#00e5a0'
  if (axisRatio < 0.9) return '#ffb020'
  return '#ff3b5c'
}

function draw(ts: number) {
  const canvas = canvasRef.value
  if (!canvas) { raf = requestAnimationFrame(draw); return }
  const ctx = canvas.getContext('2d')
  if (!ctx) { raf = requestAnimationFrame(draw); return }

  const dt = lastTs ? Math.min(0.1, (ts - lastTs) / 1000) : 0
  lastTs = ts

  // Demo animation: slow sweep.
  if (props.demo) {
    demoPhase += dt * 2
    const base = -18 + Math.sin(demoPhase) * 10 + Math.sin(demoPhase * 2.3) * 4
    rmsDb.value = base - 4
    displayPeakDb.value = base + 2
    if (displayPeakDb.value > peakHoldDb) peakHoldDb = displayPeakDb.value
  }

  // Peak hold decay.
  peakHoldDb -= props.peakDecayDbPerSec * dt
  if (peakHoldDb < props.minDb) peakHoldDb = props.minDb

  const dpr = window.devicePixelRatio || 1
  const wCss = props.width
  const hCss = props.height
  if (canvas.width !== wCss * dpr || canvas.height !== hCss * dpr) {
    canvas.width = wCss * dpr
    canvas.height = hCss * dpr
    canvas.style.width = wCss + 'px'
    canvas.style.height = hCss + 'px'
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, wCss, hCss)

  // Background.
  ctx.fillStyle = '#0e0e12' /* --meter-bg */
  ctx.fillRect(0, 0, wCss, hCss)

  const horizontal = props.orientation === 'horizontal'
  const axisLen = horizontal ? wCss : hCss
  const crossLen = horizontal ? hCss : wCss
  const gap = 2
  const cellsN = props.cells
  const rowsN = props.rows
  const cellSize = (axisLen - gap * (cellsN + 1)) / cellsN
  const rowSize = (crossLen - gap * (rowsN + 1)) / rowsN

  const rmsRatio = dbToRatio(rmsDb.value)
  const peakRatio = dbToRatio(peakHoldDb)

  for (let i = 0; i < cellsN; i++) {
    const axisRatio = (i + 1) / cellsN
    const active = axisRatio <= rmsRatio
    ctx.fillStyle = cellColour(axisRatio, active)
    if (active) {
      // Subtle glow for active cells.
      ctx.shadowColor = ctx.fillStyle as string
      ctx.shadowBlur = 4
    } else {
      ctx.shadowBlur = 0
    }
    for (let r = 0; r < rowsN; r++) {
      const x = horizontal
        ? gap + i * (cellSize + gap)
        : gap + r * (rowSize + gap)
      const y = horizontal
        ? gap + r * (rowSize + gap)
        : hCss - gap - (i + 1) * (cellSize + gap) + gap
      const w = horizontal ? cellSize : rowSize
      const h = horizontal ? rowSize : cellSize
      ctx.fillRect(x, y, w, h)
    }
  }

  // Peak hold line: brighter stripe in the cell column at peakRatio.
  ctx.shadowBlur = 0
  if (peakRatio > 0.001) {
    const idx = Math.max(0, Math.min(cellsN - 1, Math.floor(peakRatio * cellsN) - 1))
    const axisRatio = (idx + 1) / cellsN
    ctx.fillStyle = cellColour(axisRatio, true)
    const thickness = 2
    if (horizontal) {
      const x = gap + idx * (cellSize + gap) + cellSize - thickness
      ctx.fillRect(x, 1, thickness, hCss - 2)
    } else {
      const y = hCss - gap - (idx + 1) * (cellSize + gap) + gap
      ctx.fillRect(1, y, wCss - 2, thickness)
    }
  }

  raf = requestAnimationFrame(draw)
}

onMounted(() => {
  peakHoldDb = props.peak
  raf = requestAnimationFrame(draw)
})
onBeforeUnmount(() => cancelAnimationFrame(raf))

const peakLabel = computed(() => displayPeakDb.value.toFixed(1))
const rmsLabel = computed(() => rmsDb.value.toFixed(1))
</script>

<template>
  <div class="pixel-meter" :class="`pixel-meter--${orientation}`">
    <div v-if="label" class="studio-label pixel-meter__label">{{ label }}</div>
    <canvas ref="canvasRef" class="pixel-meter__canvas" aria-hidden="true" />
    <div class="pixel-meter__legend studio-value">
      <span>PEAK {{ peakLabel }} dB</span>
      <span class="pixel-meter__rms">RMS {{ rmsLabel }} dB</span>
    </div>
  </div>
</template>

<style scoped>
.pixel-meter {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.pixel-meter__canvas {
  display: block;
  border-radius: var(--radius-2);
  border: 1px solid var(--line);
  background: var(--meter-bg);
}
.pixel-meter__legend {
  display: flex;
  justify-content: space-between;
  font-variant-numeric: tabular-nums;
}
.pixel-meter__rms { color: var(--fg-1); }
.pixel-meter--vertical {
  align-items: center;
}
.pixel-meter--vertical .pixel-meter__legend {
  flex-direction: column;
  gap: 2px;
  align-items: center;
}
</style>
