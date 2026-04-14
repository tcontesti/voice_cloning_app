/**
 * useMeter — runs an rAF loop over an AnalyserNode and exposes reactive
 * RMS + peak values in dBFS. Drop-in feed for <PixelMeter>.
 *
 * Detach via stop(). We don't own the analyser, so we never disconnect it.
 */
import { onBeforeUnmount, ref, watch, type Ref } from 'vue'

export function useMeter(analyser: Ref<AnalyserNode | null | undefined>) {
  const rmsDb = ref(-60)
  const peakDb = ref(-60)
  let raf = 0
  let running = false
  let buffer = new Float32Array(2048)

  function loop() {
    const a = analyser.value
    if (!a) { raf = requestAnimationFrame(loop); return }
    if (buffer.length !== a.fftSize) buffer = new Float32Array(a.fftSize)
    a.getFloatTimeDomainData(buffer)
    let sumSq = 0
    let peak = 0
    for (let i = 0; i < buffer.length; i++) {
      const v = buffer[i]
      sumSq += v * v
      const abs = Math.abs(v)
      if (abs > peak) peak = abs
    }
    const rms = Math.sqrt(sumSq / buffer.length)
    rmsDb.value = rms > 1e-6 ? 20 * Math.log10(rms) : -60
    peakDb.value = peak > 1e-6 ? 20 * Math.log10(peak) : -60
    raf = requestAnimationFrame(loop)
  }

  function start() {
    if (running) return
    running = true
    raf = requestAnimationFrame(loop)
  }
  function stop() {
    running = false
    cancelAnimationFrame(raf)
  }

  watch(analyser, (a) => {
    if (a && !running) start()
    if (!a && running) stop()
  }, { immediate: true })

  onBeforeUnmount(stop)

  return { rmsDb, peakDb, start, stop }
}
