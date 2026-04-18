<!--
  RecorderStudio — studio-flavoured recording surface. Takes stay in memory
  (Blob + decoded AudioBuffer) until the user pushes CREATE PROFILE; at that
  point every marked take is uploaded via `recordingsApi.upload` and a
  profile is created with the resulting ids.

  Client-side SNR estimate drives the LED on each take (real SNR/LUFS from
  the backend overrides it post-upload). LUFS is not computed client-side;
  the UI shows '—' until the server returns it.

  Multi-take flow, drag&drop upload, beforeunload guard. Does NOT touch
  any backend endpoint beyond the two it already uses.
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Mic, Square, Plus, Upload, Trash2, Play, Pause, Check } from 'lucide-vue-next'

const { t } = useI18n()

import Knob from '@/ui/primitives/Knob.vue'
import LED from '@/ui/primitives/LED.vue'
import SpectrumAnalyzer from '@/ui/primitives/SpectrumAnalyzer.vue'
import PixelMeter from '@/ui/primitives/PixelMeter.vue'
import SegmentedDisplay from '@/ui/primitives/SegmentedDisplay.vue'
import TakeThumbnail from '@/ui/composites/TakeThumbnail.vue'
import DeviceSelector from '@/ui/composites/DeviceSelector.vue'

import { useRecorder, encodeWav, type RecorderResult } from '@/composables/useRecorder'
import { useMeter } from '@/composables/useMeter'
import { recordingsApi, type Recording } from '@/api/recordings'
import { profilesApi, type Profile } from '@/api/synthesis'
import { ApiError } from '@/api/client'

const MAX_TAKES = 25

export interface LocalTake {
  id: string
  blob: Blob
  url: string
  buffer: AudioBuffer | null
  durationS: number
  snrEstimateDb: number | null
  serverId: string | null
  serverSnrDb: number | null
  serverLufs: number | null
  marked: boolean
  uploading: boolean
  error: string | null
}

const emit = defineEmits<{
  (e: 'profileCreated', profile: Profile): void
}>()

const recorder = useRecorder()
const analyser = recorder.analyser
const { rmsDb, peakDb } = useMeter(analyser)

const takes = ref<LocalTake[]>([])
const takeCounter = ref(0)
const monitorLevel = ref(0.7)
const profileName = ref('')
const selectedDeviceId = ref<string | undefined>(undefined)
const deviceLabel = ref('')
const uploadBusy = ref(false)
const globalError = ref<string | null>(null)

// Decoding AudioBuffers for thumbnail + SNR reuses the recorder's
// AudioContext. A previous draft spun up a second one here for decode,
// which leaked when the user changed device (the old ctx stayed
// suspended, GC never got it). One AudioContext per component is plenty.
function getAudioCtx(): AudioContext {
  if (!recorder.audioContext.value) {
    // Recorder lazily creates the ctx on open(); if the user uploads
    // files before granting mic permission we still need one to decode.
    recorder.audioContext.value = new AudioContext()
  }
  return recorder.audioContext.value
}

async function openMic(deviceId?: string) {
  try {
    if (recorder.state.value !== 'idle') recorder.close()
    await recorder.open(deviceId)
  } catch (e) {
    globalError.value = (e as Error).message
  }
}

async function onSelectDevice(info: MediaDeviceInfo) {
  selectedDeviceId.value = info.deviceId
  deviceLabel.value = info.label
  await openMic(info.deviceId)
}

function onStartRecord() {
  if (takes.value.length >= MAX_TAKES) {
    globalError.value = t('recorder.maxTakesReached', { n: MAX_TAKES })
    return
  }
  if (recorder.state.value !== 'ready') {
    void openMic(selectedDeviceId.value).then(() => {
      if (recorder.state.value === 'ready') recorder.start()
    })
    return
  }
  recorder.start()
}

async function onStopRecord() {
  const result = recorder.stop()
  await addTakeFromResult(result)
}

async function addTakeFromResult(r: RecorderResult) {
  const take = await buildTakeFromBlob(r.blob, r.durationS)
  takes.value.push(take)
}

async function buildTakeFromBlob(blob: Blob, knownDuration?: number): Promise<LocalTake> {
  let buffer: AudioBuffer | null = null
  try {
    const arr = await blob.arrayBuffer()
    buffer = await getAudioCtx().decodeAudioData(arr.slice(0))
  } catch {
    // Some MP3/OGG may fail if the container doesn't decode in this browser;
    // we still keep the blob so the user can upload it.
    buffer = null
  }
  // Backend only accepts audio/wav (PCM). If the user dropped MP3/FLAC/OGG
  // and it decoded, re-encode the first channel as WAV so upload succeeds.
  let uploadBlob = blob
  if (buffer && blob.type !== 'audio/wav') {
    uploadBlob = encodeWav(buffer.getChannelData(0), buffer.sampleRate)
  }
  const url = URL.createObjectURL(uploadBlob)
  const snr = buffer ? estimateSnrDb(buffer) : null
  takeCounter.value += 1
  return {
    id: `local-${takeCounter.value}-${Date.now().toString(36)}`,
    blob: uploadBlob,
    url,
    buffer,
    durationS: knownDuration ?? (buffer ? buffer.duration : 0),
    snrEstimateDb: snr,
    serverId: null,
    serverSnrDb: null,
    serverLufs: null,
    marked: true,
    uploading: false,
    error: null,
  }
}

/** Rough SNR estimate: RMS of loudest 20% of 20 ms frames over quietest 20%. */
function estimateSnrDb(buf: AudioBuffer): number {
  const sr = buf.sampleRate
  const data = buf.getChannelData(0)
  const frameSize = Math.max(1, Math.floor(sr * 0.02))
  const frames: number[] = []
  for (let i = 0; i + frameSize <= data.length; i += frameSize) {
    let s = 0
    for (let j = 0; j < frameSize; j++) s += data[i + j] * data[i + j]
    frames.push(Math.sqrt(s / frameSize))
  }
  if (frames.length < 5) return 0
  frames.sort((a, b) => a - b)
  const loFloor = Math.max(1, Math.floor(frames.length * 0.2))
  const hiFloor = Math.max(1, Math.floor(frames.length * 0.2))
  let noise = 0
  for (let i = 0; i < loFloor; i++) noise += frames[i] * frames[i]
  noise = Math.sqrt(noise / loFloor)
  let signal = 0
  for (let i = frames.length - hiFloor; i < frames.length; i++) signal += frames[i] * frames[i]
  signal = Math.sqrt(signal / hiFloor)
  if (noise < 1e-9 || signal < 1e-9) return 0
  return Math.max(0, 20 * Math.log10(signal / noise))
}

async function onUploadFiles(files: FileList) {
  for (const f of Array.from(files)) {
    if (takes.value.length >= MAX_TAKES) break
    try {
      const take = await buildTakeFromBlob(f)
      takes.value.push(take)
    } catch (e) {
      globalError.value = t('recorder.decodeFailed', {
        name: f.name,
        reason: (e as Error).message,
      })
    }
  }
}

function onDragOver(e: DragEvent) {
  e.preventDefault()
}
function onDrop(e: DragEvent) {
  e.preventDefault()
  if (e.dataTransfer?.files.length) void onUploadFiles(e.dataTransfer.files)
}

// Active HTMLAudioElement per take id. We hold the reference so deleting
// a take can pause + detach the src BEFORE revokeObjectURL, otherwise the
// player emits an opaque NotSupportedError mid-playback when the blob URL
// vanishes under it.
const playing = new Map<string, HTMLAudioElement>()
// Which take is currently playing (for Play→Pause toggle rendering) and
// per-take progress in [0, 1] so TakeThumbnail can draw the red playhead.
const currentPlayingId = ref<string | null>(null)
const progressById = ref<Record<string, number>>({})

function stopPlayback(id: string) {
  const a = playing.get(id)
  if (!a) return
  try {
    a.pause()
    a.src = ''   // release the object URL handle before revoke
    a.load()
  } catch { /* noop */ }
  playing.delete(id)
  if (currentPlayingId.value === id) currentPlayingId.value = null
}

function deleteTake(id: string) {
  const idx = takes.value.findIndex((t) => t.id === id)
  if (idx < 0) return
  stopPlayback(id)
  delete progressById.value[id]
  URL.revokeObjectURL(takes.value[idx].url)
  takes.value.splice(idx, 1)
}

function toggleMark(id: string) {
  const t = takes.value.find((x) => x.id === id)
  if (t) t.marked = !t.marked
}

function togglePlayTake(id: string) {
  const existing = playing.get(id)
  if (existing && !existing.paused) {
    existing.pause()
    currentPlayingId.value = null
    return
  }
  // Stop any other take so only one plays at a time.
  for (const otherId of playing.keys()) {
    if (otherId !== id) stopPlayback(otherId)
  }
  if (existing && existing.paused) {
    void existing.play().then(() => { currentPlayingId.value = id })
    return
  }
  const t = takes.value.find((x) => x.id === id)
  if (!t) return
  const audio = new Audio(t.url)
  const onTime = () => {
    const d = audio.duration
    progressById.value[id] = d > 0 && isFinite(d) ? audio.currentTime / d : 0
  }
  const onEnd = () => {
    progressById.value[id] = 0
    currentPlayingId.value = null
  }
  audio.addEventListener('timeupdate', onTime)
  audio.addEventListener('ended', onEnd, { once: true })
  audio.addEventListener('pause', () => {
    if (currentPlayingId.value === id && audio.paused && !audio.ended) {
      currentPlayingId.value = null
    }
  })
  audio.addEventListener('error', () => {
    playing.delete(id)
    if (currentPlayingId.value === id) currentPlayingId.value = null
  }, { once: true })
  playing.set(id, audio)
  void audio.play()
    .then(() => { currentPlayingId.value = id })
    .catch(() => { playing.delete(id) })
}

function seekTake(id: string, ratio: number) {
  const audio = playing.get(id)
  const t = takes.value.find((x) => x.id === id)
  // Click-to-seek works before first play too — duration comes from the
  // decoded AudioBuffer in that case. Start playback from the click
  // position if nothing's playing yet, otherwise just move currentTime.
  if (!audio) {
    togglePlayTake(id)
    // Next tick: the newly created audio needs its metadata before seek.
    // Simpler: wait for loadedmetadata. For WAV blobs it's usually instant.
    const a = playing.get(id)
    if (!a) return
    const apply = () => {
      const d = a.duration || t?.durationS || 0
      if (d > 0) a.currentTime = Math.max(0, Math.min(d, ratio * d))
    }
    if (a.readyState >= 1) apply()
    else a.addEventListener('loadedmetadata', apply, { once: true })
    return
  }
  const d = audio.duration || t?.durationS || 0
  if (d > 0) audio.currentTime = Math.max(0, Math.min(d, ratio * d))
  progressById.value[id] = ratio
}

const markedCount = computed(() => takes.value.filter((t) => t.marked).length)
const hasUnsaved = computed(() => takes.value.some((t) => !t.serverId))

function snrColour(db: number | null): 'green' | 'amber' | 'red' | 'off' {
  if (db === null) return 'off'
  if (db >= 15) return 'green'
  if (db >= 10) return 'amber'
  return 'red'
}

async function createProfile() {
  if (!markedCount.value) {
    globalError.value = t('recorder.markAtLeastOne')
    return
  }
  uploadBusy.value = true
  globalError.value = null
  const referenceIds: string[] = []
  try {
    for (const t of takes.value) {
      if (!t.marked) continue
      if (t.serverId) { referenceIds.push(t.serverId); continue }
      t.uploading = true
      t.error = null
      try {
        const rec: Recording = await recordingsApi.upload(t.blob, `take-${t.id}.wav`)
        t.serverId = rec.id
        t.serverSnrDb = rec.snr_db ?? null
        t.serverLufs = rec.lufs ?? null
        referenceIds.push(rec.id)
      } catch (e) {
        t.error = e instanceof ApiError ? String(e.detail ?? 'error') : (e as Error).message
      } finally {
        t.uploading = false
      }
    }
    if (!referenceIds.length) {
      globalError.value = t('recorder.noTakeUploaded')
      return
    }
    const name = profileName.value.trim() ||
      `${t('recorder.autoProfileNamePrefix')} ${new Date().toISOString().slice(0, 16)}`
    const profile = await profilesApi.create(name, referenceIds)
    emit('profileCreated', profile)
    // Marcamos todo como synced sin borrar (el usuario puede seguir iterando).
  } catch (e) {
    globalError.value = e instanceof ApiError ? String(e.detail ?? 'error') : (e as Error).message
  } finally {
    uploadBusy.value = false
  }
}

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (!hasUnsaved.value) return
  e.preventDefault()
  e.returnValue = ''
}

onMounted(() => {
  window.addEventListener('beforeunload', onBeforeUnload)
  // Best-effort: try silent mic open so the analyser feeds the spectrum/meter.
  // If permission is denied, user can still pick a device or upload files.
  void openMic()
})
onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
  for (const t of takes.value) {
    stopPlayback(t.id)
    URL.revokeObjectURL(t.url)
  }
  // recorder.close() owns the AudioContext lifecycle — don't double-close.
  recorder.close()
})

watch(() => recorder.state.value, (s) => {
  if (s === 'error') globalError.value = recorder.error.value ?? 'Error de audio.'
})

const isRecording = computed(() => recorder.state.value === 'recording')
const statusText = computed(() => {
  switch (recorder.state.value) {
    case 'recording': return 'REC'
    case 'ready':     return 'READY'
    case 'permission': return 'PERMISSION'
    case 'error':     return 'ERROR'
    default:          return 'IDLE'
  }
})
</script>

<template>
  <div class="rs" @dragover="onDragOver" @drop="onDrop">
    <header class="rs__header">
      <div class="rs__titleblock">
        <div class="studio-label">RECORDER STUDIO</div>
        <div class="display-2 rs__title">Capturar voz de referencia</div>
      </div>
      <div class="rs__status">
        <SegmentedDisplay :text="statusText" :tint="isRecording ? 'red' : 'green'" size="md" label="ESTADO" :blink="isRecording" />
        <DeviceSelector :active-device-id="selectedDeviceId" :active-label="deviceLabel"
                        @select-device="onSelectDevice" @upload-files="onUploadFiles" />
      </div>
    </header>

    <section class="rs__analyser studio-card">
      <SpectrumAnalyzer :analyser="analyser" :height="260" :width="960" label="SPECTRUM · 20 Hz – 20 kHz" />
    </section>

    <section class="rs__mixer studio-card">
      <div class="rs__meters">
        <PixelMeter orientation="horizontal" :width="480" :height="48"
                    :cells="48" :rows="5" :rms="rmsDb" :peak="peakDb" label="INPUT" />
      </div>
      <div class="rs__controls">
        <Knob v-model="monitorLevel" :min="0" :max="1" :step="0.01" :default="0.7"
              label="MONITOR" :size="48" :precision="2" />
        <div class="rs__actions">
          <button type="button" class="rs__btn rs__btn--rec" :class="{ 'rs__btn--active': isRecording }"
                  :disabled="takes.length >= MAX_TAKES"
                  @click="isRecording ? onStopRecord() : onStartRecord()">
            <component :is="isRecording ? Square : Mic" class="w-4 h-4" />
            <LED color="red" :on="isRecording" :pulse="isRecording" size="xs" />
            <span>{{ isRecording ? 'STOP' : 'REC' }}</span>
          </button>
          <button type="button" class="rs__btn" :disabled="isRecording || takes.length >= MAX_TAKES"
                  @click="onStartRecord">
            <Plus class="w-4 h-4" /><span>NEW TAKE</span>
          </button>
          <label class="rs__btn">
            <Upload class="w-4 h-4" /><span>UPLOAD</span>
            <input type="file" hidden multiple accept=".wav,.mp3,.flac,.ogg,audio/*"
                   @change="(e) => (e.target as HTMLInputElement).files && onUploadFiles(((e.target as HTMLInputElement).files)!)" />
          </label>
        </div>
      </div>
    </section>

    <section class="rs__takes studio-card">
      <div class="rs__takes-header">
        <div class="studio-label">TAKES · {{ takes.length }} / {{ MAX_TAKES }}</div>
        <div class="studio-value">MARCADAS {{ markedCount }}</div>
      </div>

      <div v-if="!takes.length" class="rs__empty">
        Graba una take o arrastra archivos aquí. Se quedan en memoria del navegador
        hasta que pulses CREATE PROFILE.
      </div>

      <ol v-else class="rs__take-list">
        <li v-for="(t, i) in takes" :key="t.id" class="rs__take" :class="{ 'rs__take--marked': t.marked }">
          <div class="rs__take-index studio-value">{{ String(i + 1).padStart(2, '0') }}</div>
          <TakeThumbnail
            :buffer="t.buffer"
            :width="320"
            :height="48"
            :progress="progressById[t.id] ?? 0"
            interactive
            @seek="(r: number) => seekTake(t.id, r)"
          />
          <div class="rs__take-meta">
            <div class="studio-value">{{ t.durationS.toFixed(1) }}s</div>
            <div class="rs__take-snr">
              <LED :color="snrColour(t.serverSnrDb ?? t.snrEstimateDb)" size="xs" />
              <span class="studio-value">
                SNR {{ (t.serverSnrDb ?? t.snrEstimateDb)?.toFixed(1) ?? '—' }} dB
              </span>
            </div>
            <div class="studio-value rs__take-lufs">
              LUFS {{ t.serverLufs?.toFixed(1) ?? '—' }}
            </div>
          </div>
          <div class="rs__take-actions">
            <button type="button" class="rs__icon-btn"
                    :class="{ 'rs__icon-btn--active': currentPlayingId === t.id }"
                    :aria-label="currentPlayingId === t.id ? 'Pausar' : 'Reproducir'"
                    @click="togglePlayTake(t.id)">
              <component :is="currentPlayingId === t.id ? Pause : Play" class="w-4 h-4" />
            </button>
            <button type="button" class="rs__icon-btn"
                    :class="{ 'rs__icon-btn--active': t.marked }"
                    aria-label="Marcar como referencia" @click="toggleMark(t.id)">
              <Check class="w-4 h-4" />
            </button>
            <button type="button" class="rs__icon-btn rs__icon-btn--danger" aria-label="Eliminar" @click="deleteTake(t.id)">
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
          <div v-if="t.uploading" class="rs__take-upload studio-value">subiendo…</div>
          <div v-else-if="t.error" class="rs__take-error studio-value">{{ t.error }}</div>
          <div v-else-if="t.serverId" class="rs__take-ok studio-value">synced</div>
        </li>
      </ol>
    </section>

    <section class="rs__create studio-card">
      <div class="rs__create-inputs">
        <label class="studio-label" for="rs-name">NOMBRE DEL PERFIL</label>
        <input id="rs-name" v-model="profileName" class="input rs__name-input"
               placeholder="ej. Voz paciente pre-op" :disabled="uploadBusy" />
      </div>
      <div class="rs__create-stats studio-value">
        {{ markedCount }} take(s) marcada(s) · {{ MAX_TAKES }} máx
      </div>
      <button type="button" class="btn btn-primary rs__create-btn"
              :disabled="uploadBusy || !markedCount" @click="createProfile">
        <Check class="w-4 h-4" />
        {{ uploadBusy ? 'Creando…' : 'CREATE PROFILE' }}
      </button>
    </section>

    <p v-if="globalError" class="rs__error" role="alert">{{ globalError }}</p>
  </div>
</template>

<style scoped>
.rs {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 1200px;
  margin: 0 auto;
}
.rs__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}
.rs__title { margin: 0; color: var(--fg-0); }
.rs__status {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}
.rs__analyser { padding: 20px; }
.rs__analyser :deep(.spectrum__canvas) { width: 100%; }

.rs__mixer {
  padding: 20px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 24px;
  align-items: center;
}
.rs__meters { min-width: 320px; }
.rs__controls { display: flex; align-items: center; gap: 24px; }
.rs__actions { display: flex; gap: 10px; }
.rs__btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--fg-0);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: transform var(--dur-base) var(--ease-studio),
              background var(--dur-base) var(--ease-studio),
              border-color var(--dur-base) var(--ease-studio);
}
.rs__btn:hover:not(:disabled) { background: var(--bg-3); border-color: var(--line-2); transform: translateY(-1px); }
.rs__btn:disabled { opacity: 0.4; cursor: not-allowed; }
.rs__btn--rec {
  background: color-mix(in srgb, var(--signal-red) 22%, var(--bg-2));
  border-color: var(--signal-red);
}
.rs__btn--active { box-shadow: 0 0 18px color-mix(in srgb, var(--signal-red) 40%, transparent); }

.rs__takes { padding: 20px; }
.rs__takes-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 12px;
}
.rs__empty {
  padding: 32px;
  text-align: center;
  color: var(--fg-2);
  border: 1px dashed var(--line);
  border-radius: var(--radius-3);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.05em;
}
.rs__take-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.rs__take {
  display: grid;
  grid-template-columns: 36px 320px 1fr auto;
  gap: 16px;
  align-items: center;
  padding: 10px 12px;
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-radius: var(--radius-3);
  transition: border-color var(--dur-base) var(--ease-studio);
}
.rs__take--marked { border-color: var(--accent); }
.rs__take-meta {
  display: flex;
  gap: 18px;
  color: var(--fg-1);
  font-variant-numeric: tabular-nums;
}
.rs__take-snr { display: flex; align-items: center; gap: 6px; }
.rs__take-lufs { color: var(--fg-2); }
.rs__take-actions { display: flex; gap: 6px; }
.rs__icon-btn {
  width: 32px; height: 32px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--bg-3);
  border: 1px solid var(--line);
  border-radius: var(--radius-2);
  color: var(--fg-1);
  cursor: pointer;
  transition: background var(--dur-base) var(--ease-studio),
              color var(--dur-base) var(--ease-studio),
              border-color var(--dur-base) var(--ease-studio);
}
.rs__icon-btn:hover { color: var(--fg-0); border-color: var(--line-2); }
.rs__icon-btn--active {
  color: var(--fg-0);
  background: color-mix(in srgb, var(--accent) 20%, var(--bg-3));
  border-color: var(--accent);
}
.rs__icon-btn--danger:hover { color: var(--signal-red); border-color: var(--signal-red); }
.rs__take-upload { grid-column: 2 / -1; color: var(--signal-amber); }
.rs__take-error { grid-column: 2 / -1; color: var(--signal-red); }
.rs__take-ok { grid-column: 2 / -1; color: var(--signal-green); }

.rs__create {
  padding: 20px;
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 20px;
  align-items: end;
}
.rs__create-stats { color: var(--fg-1); }
.rs__name-input { margin-top: 6px; }
.rs__create-btn {
  padding: 12px 24px;
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.1em;
}

.rs__error {
  padding: 12px 16px;
  background: color-mix(in srgb, var(--signal-red) 12%, var(--bg-1));
  border: 1px solid var(--signal-red);
  border-radius: var(--radius-3);
  color: var(--signal-red);
  font-family: var(--font-mono);
  font-size: 12px;
}
</style>
