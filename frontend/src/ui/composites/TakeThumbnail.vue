<!--
  TakeThumbnail — tiny canvas waveform drawn from a pre-decoded
  AudioBuffer. Used inside RecorderStudio take rows so we don't spin up
  a full WaveSurfer instance per take.

  When `progress` (0..1) and `interactive` are set it also shows a red
  playhead and forwards clicks as a seek event — parent decides what to
  do with the ratio (usually setting audio.currentTime).
-->
<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    buffer: AudioBuffer | null
    width?: number
    height?: number
    color?: string
    progress?: number
    interactive?: boolean
  }>(),
  {
    width: 320,
    height: 48,
    color: 'rgba(245, 245, 247, 0.7)',
    progress: 0,
    interactive: false,
  },
)

const emit = defineEmits<{
  (e: 'seek', ratio: number): void
}>()

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
  if (buf) {
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
  // Playhead is drawn on top so it tracks the buffer draw above. We
  // redraw on progress change so a ref/watch stays cheap — the buffer
  // pass is short for take-sized canvases (<= 320px wide).
  if (props.progress > 0 && props.progress < 1) {
    const x = Math.floor(props.progress * props.width)
    ctx.fillStyle = '#ff3b5c'
    ctx.fillRect(x, 0, 2, props.height)
  }
}

function onClick(e: MouseEvent) {
  if (!props.interactive) return
  const el = e.currentTarget as HTMLCanvasElement
  const rect = el.getBoundingClientRect()
  const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
  emit('seek', ratio)
}

onMounted(draw)
watch(() => props.buffer, draw)
watch(() => props.progress, draw)
watch(() => [props.width, props.height], draw)
</script>

<template>
  <canvas
    ref="canvasRef"
    class="take-thumb"
    :class="{ 'take-thumb--interactive': interactive }"
    :aria-hidden="interactive ? undefined : true"
    :role="interactive ? 'slider' : undefined"
    @click="onClick"
  />
</template>

<style scoped>
.take-thumb {
  display: block;
  border-radius: var(--radius-2);
  border: 1px solid var(--line);
}
.take-thumb--interactive { cursor: pointer; }
.take-thumb--interactive:hover { border-color: var(--line-2); }
</style>
