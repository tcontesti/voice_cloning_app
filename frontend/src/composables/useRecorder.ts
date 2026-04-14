/**
 * Mic capture → MediaRecorder → WAV (PCM 16-bit mono 16 kHz) blob.
 *
 * The browser only emits Opus/WebM in MediaRecorder; for WAV output we
 * record raw Float32 chunks via a ScriptProcessorNode (deprecated but
 * universally supported), then encode WAV at stop().
 *
 * AudioContext is shared so the spectrogram analyser and VU can tap into
 * the same source without re-asking for getUserMedia.
 */
import { ref, shallowRef } from 'vue'

export type RecorderState = 'idle' | 'permission' | 'ready' | 'recording' | 'stopped' | 'error'

export interface RecorderResult {
  blob: Blob
  durationS: number
  sampleRate: number
}

const TARGET_SR = 16000

function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const bytesPerSample = 2
  const blockAlign = bytesPerSample
  const byteRate = sampleRate * blockAlign
  const dataSize = samples.length * bytesPerSample
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  const writeString = (off: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i))
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)             // PCM
  view.setUint16(22, 1, true)             // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, byteRate, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, 16, true)
  writeString(36, 'data')
  view.setUint32(40, dataSize, true)

  let off = 44
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(off, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    off += 2
  }

  return new Blob([buffer], { type: 'audio/wav' })
}

function downsampleTo16k(input: Float32Array, fromRate: number): Float32Array {
  if (fromRate === TARGET_SR) return input
  const ratio = fromRate / TARGET_SR
  const outLen = Math.floor(input.length / ratio)
  const out = new Float32Array(outLen)
  for (let i = 0; i < outLen; i++) {
    const idx = Math.floor(i * ratio)
    // simple decimation (ok for ref material; webrtcvad runs fine)
    out[i] = input[idx]
  }
  return out
}

export function useRecorder() {
  const state = ref<RecorderState>('idle')
  const error = ref<string | null>(null)
  const audioContext = shallowRef<AudioContext | null>(null)
  const sourceNode = shallowRef<MediaStreamAudioSourceNode | null>(null)
  const analyser = shallowRef<AnalyserNode | null>(null)

  let stream: MediaStream | null = null
  let processor: ScriptProcessorNode | null = null
  let chunks: Float32Array[] = []
  let captureRate = TARGET_SR

  async function open(deviceId?: string) {
    state.value = 'permission'
    error.value = null
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: deviceId ? { exact: deviceId } : undefined,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: false,
          channelCount: 1,
        },
      })
      const ctx = new AudioContext()
      audioContext.value = ctx
      captureRate = ctx.sampleRate
      const src = ctx.createMediaStreamSource(stream)
      sourceNode.value = src

      const ana = ctx.createAnalyser()
      ana.fftSize = 1024
      ana.smoothingTimeConstant = 0.6
      src.connect(ana)
      analyser.value = ana

      state.value = 'ready'
    } catch (e) {
      state.value = 'error'
      error.value = (e as Error).message
      throw e
    }
  }

  function start() {
    if (!audioContext.value || !sourceNode.value) throw new Error('recorder not opened')
    chunks = []
    processor = audioContext.value.createScriptProcessor(4096, 1, 1)
    processor.onaudioprocess = (ev) => {
      // Copy: the underlying buffer is reused.
      chunks.push(new Float32Array(ev.inputBuffer.getChannelData(0)))
    }
    sourceNode.value.connect(processor)
    processor.connect(audioContext.value.destination)
    state.value = 'recording'
  }

  function stop(): RecorderResult {
    if (processor) {
      processor.disconnect()
      sourceNode.value?.disconnect(processor)
      processor.onaudioprocess = null
      processor = null
    }
    state.value = 'stopped'
    const total = chunks.reduce((acc, c) => acc + c.length, 0)
    const merged = new Float32Array(total)
    let off = 0
    for (const c of chunks) { merged.set(c, off); off += c.length }
    const samples = downsampleTo16k(merged, captureRate)
    return {
      blob: encodeWav(samples, TARGET_SR),
      durationS: samples.length / TARGET_SR,
      sampleRate: TARGET_SR,
    }
  }

  function close() {
    try { processor?.disconnect() } catch {}
    try { sourceNode.value?.disconnect() } catch {}
    try { analyser.value?.disconnect() } catch {}
    stream?.getTracks().forEach((t) => t.stop())
    void audioContext.value?.close()
    audioContext.value = null
    sourceNode.value = null
    analyser.value = null
    stream = null
    state.value = 'idle'
  }

  return { state, error, audioContext, analyser, open, start, stop, close }
}
