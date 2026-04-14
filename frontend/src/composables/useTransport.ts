/**
 * useTransport — shared play/pause/stop state. Currently a thin singleton
 * so the TransportBar and WaveformTimeline stay in sync without prop
 * drilling. Not audio-graph aware — that's the caller's job.
 */
import { ref } from 'vue'

type TransportState = 'stopped' | 'playing' | 'paused' | 'recording'

const state = ref<TransportState>('stopped')
const timeS = ref(0)
const loop = ref(false)

export function useTransport() {
  function play() { state.value = 'playing' }
  function pause() { state.value = 'paused' }
  function stop() { state.value = 'stopped'; timeS.value = 0 }
  function record() { state.value = 'recording'; timeS.value = 0 }
  function toggleLoop() { loop.value = !loop.value }
  function setTime(t: number) { timeS.value = t }

  return { state, timeS, loop, play, pause, stop, record, toggleLoop, setTime }
}

export function formatTimecode(s: number): string {
  if (!Number.isFinite(s) || s < 0) s = 0
  const mm = Math.floor(s / 60)
  const ss = Math.floor(s % 60)
  const ms = Math.floor((s - Math.floor(s)) * 1000)
  return `${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}.${String(ms).padStart(3, '0')}`
}
