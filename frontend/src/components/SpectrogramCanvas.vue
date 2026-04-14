<script setup lang="ts">
/**
 * Real-time spectrogram via AnalyserNode.getByteFrequencyData() (1024-bin FFT).
 * Scrolls left every animation frame; viridis colormap; log frequency axis.
 *
 * Not a full mel-spectrogram (would need an AudioWorklet + custom mel filterbank).
 * Visually equivalent for monitoring; if clinical needs justify mel-scale we
 * upgrade in M5+.
 */
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps<{
  analyser: AnalyserNode | null
  height?: number
}>()

const canvas = ref<HTMLCanvasElement | null>(null)
let raf = 0
let ctx2d: CanvasRenderingContext2D | null = null
let buf: Uint8Array | null = null

// 8-stop viridis approximation
const viridis: [number, number, number][] = [
  [68, 1, 84], [72, 35, 116], [64, 67, 135], [52, 94, 141],
  [41, 120, 142], [32, 144, 140], [34, 167, 132], [68, 190, 112],
]

function color(v: number): string {
  const x = Math.max(0, Math.min(1, v / 255))
  const idx = x * (viridis.length - 1)
  const i = Math.floor(idx)
  const frac = idx - i
  const a = viridis[i]
  const b = viridis[Math.min(i + 1, viridis.length - 1)]
  const r = Math.round(a[0] + (b[0] - a[0]) * frac)
  const g = Math.round(a[1] + (b[1] - a[1]) * frac)
  const bl = Math.round(a[2] + (b[2] - a[2]) * frac)
  return `rgb(${r},${g},${bl})`
}

function paintFrame() {
  if (!props.analyser || !canvas.value || !ctx2d) return
  const w = canvas.value.width
  const h = canvas.value.height

  if (!buf || buf.length !== props.analyser.frequencyBinCount) {
    buf = new Uint8Array(props.analyser.frequencyBinCount)
  }
  props.analyser.getByteFrequencyData(buf)

  // Scroll left by 1px
  const img = ctx2d.getImageData(1, 0, w - 1, h)
  ctx2d.putImageData(img, 0, 0)

  // Draw new column at right
  const bins = buf.length
  for (let y = 0; y < h; y++) {
    // log frequency mapping (low freq → bottom)
    const t = y / h
    const binIdx = Math.floor(Math.pow(10, t * Math.log10(bins)) - 1)
    const v = buf[Math.max(0, Math.min(bins - 1, binIdx))]
    ctx2d.fillStyle = color(v)
    ctx2d.fillRect(w - 1, h - 1 - y, 1, 1)
  }

  raf = requestAnimationFrame(paintFrame)
}

function resize() {
  if (!canvas.value) return
  const dpr = window.devicePixelRatio || 1
  const rect = canvas.value.getBoundingClientRect()
  canvas.value.width = Math.floor(rect.width * dpr)
  canvas.value.height = Math.floor((props.height ?? 120) * dpr)
  canvas.value.style.height = `${props.height ?? 120}px`
  ctx2d = canvas.value.getContext('2d')
  if (ctx2d) {
    ctx2d.fillStyle = 'rgb(24,24,27)'
    ctx2d.fillRect(0, 0, canvas.value.width, canvas.value.height)
  }
}

watch(() => props.analyser, (a) => {
  cancelAnimationFrame(raf)
  if (a) {
    resize()
    raf = requestAnimationFrame(paintFrame)
  }
})

onMounted(() => {
  resize()
  window.addEventListener('resize', resize)
  if (props.analyser) raf = requestAnimationFrame(paintFrame)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('resize', resize)
})
</script>

<template>
  <canvas ref="canvas" class="w-full rounded-lg block bg-zinc-900" />
</template>
