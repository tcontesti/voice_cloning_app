<!--
  WaveformTimeline — wavesurfer.js 7 wrapper styled to the studio look.
  Accepts a Blob or URL; emits time/duration and play state. Drag to seek.

  Kept deliberately thin: no regions, no zoom controls yet — composites
  layer those on top when needed (RecorderStudio provides thumbnails and
  the synthesis player uses the full version).
-->
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import WaveSurfer from 'wavesurfer.js'

const props = withDefaults(
  defineProps<{
    src?: Blob | string | null
    height?: number
    barWidth?: number
    barGap?: number
    barRadius?: number
    waveColor?: string
    progressColor?: string
    interact?: boolean
    autoPlay?: boolean
  }>(),
  {
    height: 96,
    barWidth: 1,
    barGap: 1,
    barRadius: 1,
    waveColor: 'rgba(245, 245, 247, 0.55)',
    progressColor: '#a88aff',
    interact: true,
  },
)

const emit = defineEmits<{
  (e: 'ready', duration: number): void
  (e: 'timeupdate', time: number): void
  (e: 'play'): void
  (e: 'pause'): void
  (e: 'finish'): void
}>()

const container = ref<HTMLDivElement | null>(null)
let ws: WaveSurfer | null = null

function destroy() {
  try { ws?.destroy() } catch { /* noop */ }
  ws = null
}

async function load() {
  if (!container.value) return
  destroy()
  if (!props.src) return
  ws = WaveSurfer.create({
    container: container.value,
    height: props.height,
    waveColor: props.waveColor,
    progressColor: props.progressColor,
    cursorColor: '#ff3b5c',
    cursorWidth: 2,
    barWidth: props.barWidth,
    barGap: props.barGap,
    barRadius: props.barRadius,
    interact: props.interact,
    normalize: true,
  })
  ws.on('ready', () => emit('ready', ws?.getDuration() ?? 0))
  ws.on('timeupdate', (t) => emit('timeupdate', t))
  ws.on('play', () => emit('play'))
  ws.on('pause', () => emit('pause'))
  ws.on('finish', () => emit('finish'))
  if (props.src instanceof Blob) {
    await ws.loadBlob(props.src)
  } else {
    await ws.load(props.src)
  }
  if (props.autoPlay) void ws.play()
}

function playPause() { ws?.playPause() }
function stop() { ws?.stop() }
function seek(ratio: number) { ws?.seekTo(Math.max(0, Math.min(1, ratio))) }
function isPlaying() { return !!ws?.isPlaying() }

defineExpose({ playPause, stop, seek, isPlaying })

onMounted(load)
onBeforeUnmount(destroy)
watch(() => props.src, load)
</script>

<template>
  <div class="wft studio-surface" aria-label="waveform">
    <div ref="container" class="wft__canvas" />
  </div>
</template>

<style scoped>
.wft {
  padding: 8px 10px;
  background: var(--bg-2);
  border-radius: var(--radius-3);
}
.wft__canvas { width: 100%; }
</style>
