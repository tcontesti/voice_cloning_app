/**
 * useAudioGraph — tiny wrapper around a single AudioContext so meters,
 * spectrum and the recorder can share one analyser chain without each
 * pulling their own getUserMedia.
 *
 * Not a full mixer. For this iteration we expose one analyser per source
 * and let individual composables (useMeter / useSpectrum) tap into it.
 */
import { ref, shallowRef } from 'vue'

export interface AudioGraphSource {
  sourceNode: AudioNode
  analyser: AnalyserNode
  stream?: MediaStream
  close(): void
}

function ensureContext(existing: AudioContext | null): AudioContext {
  if (existing && existing.state !== 'closed') return existing
  return new AudioContext()
}

export function useAudioGraph() {
  const context = shallowRef<AudioContext | null>(null)
  const error = ref<string | null>(null)

  async function attachMediaStream(stream: MediaStream): Promise<AudioGraphSource> {
    const ctx = ensureContext(context.value)
    context.value = ctx
    const src = ctx.createMediaStreamSource(stream)
    const ana = ctx.createAnalyser()
    ana.fftSize = 2048
    ana.smoothingTimeConstant = 0.75
    src.connect(ana)
    return {
      sourceNode: src,
      analyser: ana,
      stream,
      close() {
        try { ana.disconnect() } catch { /* noop */ }
        try { src.disconnect() } catch { /* noop */ }
        stream.getTracks().forEach((t) => t.stop())
      },
    }
  }

  async function attachBuffer(buf: AudioBuffer): Promise<AudioGraphSource> {
    const ctx = ensureContext(context.value)
    context.value = ctx
    const src = ctx.createBufferSource()
    src.buffer = buf
    const ana = ctx.createAnalyser()
    ana.fftSize = 2048
    src.connect(ana)
    ana.connect(ctx.destination)
    src.start()
    return {
      sourceNode: src,
      analyser: ana,
      close() {
        try { src.stop() } catch { /* noop */ }
        try { src.disconnect() } catch { /* noop */ }
        try { ana.disconnect() } catch { /* noop */ }
      },
    }
  }

  function close() {
    try { void context.value?.close() } catch { /* noop */ }
    context.value = null
  }

  return { context, error, attachMediaStream, attachBuffer, close }
}
