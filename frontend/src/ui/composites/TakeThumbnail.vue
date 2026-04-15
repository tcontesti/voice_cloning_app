<!--
  TakeThumbnail — tiny canvas waveform drawn from a pre-decoded
  AudioBuffer. Purely cosmetic (not seekable). Used inside RecorderStudio
  take rows so we don't spin up a full WaveSurfer instance per take.
-->
<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    buffer: AudioBuffer | null
    width?: number
    height?: number
    color?: string
  }>(),
  { width: 320, height: 48, color: 'rgba(245, 245, 247, 0.7)' },
)

const canvasRef = ref<HTMLCanvasElement | null>(null)

function draw() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const dpr = window.devicePixelRatio || 1
  canvas.width = props.width * dpr
  canvas.height = props.height * dpr
  canvas.style.width = props.width + 'px'
  canvas.style.height = props.height + 'px'
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, props.width, props.height)
  ctx.fillStyle = '#0e0e12'
  ctx.fillRect(0, 0, props.width, props.height)
  const buf = props.buffer
  if (!buf) return

  const data = buf.getChannelData(0)
  const midY = props.height / 2
  const step = Math.max(1, Math.floor(data.length / props.width))
  ctx.fillStyle = props.color
  for (let x = 0; x < props.width; x++) {
    let peak = 0
    const start = x * step
    const end = Math.min(data.length, start + step)
    for (let i = start; i < end; i++) {
      const v = Math.abs(data[i])
      if (v > peak) peak = v
    }
    const h = Math.max(1, peak * midY)
    ctx.fillRect(x, midY - h, 1, h * 2)
  }
}

onMounted(draw)
watch(() => props.buffer, draw)
</script>

<template>
  <canvas ref="canvasRef" class="take-thumb" aria-hidden="true" />
</template>

<style scoped>
.take-thumb {
  display: block;
  border-radius: var(--radius-2);
  border: 1px solid var(--line);
}
</style>
