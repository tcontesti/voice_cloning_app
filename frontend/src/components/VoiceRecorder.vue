<script setup lang="ts">
/**
 * Self-contained voice recorder. Emits `recorded` with WAV blob + metrics.
 *
 * - Device picker (auto-fetch on mount, refresh after first permission grant)
 * - Live waveform via WaveSurfer 7 record plugin
 * - Live spectrogram + VU meter tapping the same AudioContext
 * - Records at the device rate; downsamples to 16 kHz mono WAV at stop()
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Mic, Square, RotateCcw, Save } from 'lucide-vue-next'
import WaveSurfer from 'wavesurfer.js'
import RecordPlugin from 'wavesurfer.js/dist/plugins/record.js'
import { useRecorder, type RecorderResult } from '@/composables/useRecorder'
import { useAudioInputDevices } from '@/composables/useDevices'
import VuMeter from './VuMeter.vue'
import SpectrogramCanvas from './SpectrogramCanvas.vue'

const emit = defineEmits<{
  recorded: [result: RecorderResult]
  error: [message: string]
}>()

const { t } = useI18n()
const { devices, refresh: refreshDevices } = useAudioInputDevices()
const recorder = useRecorder()

const selectedDeviceId = ref<string>('')
const wave = ref<HTMLDivElement | null>(null)
let ws: WaveSurfer | null = null
let record: any = null
const lastResult = ref<RecorderResult | null>(null)

const isRecording = computed(() => recorder.state.value === 'recording')

async function ensureOpen() {
  if (recorder.state.value === 'idle' || recorder.state.value === 'error') {
    await recorder.open(selectedDeviceId.value || undefined)
    await refreshDevices() // labels populate after first grant
    setupWavesurfer()
  }
}

function setupWavesurfer() {
  if (ws || !wave.value) return
  ws = WaveSurfer.create({
    container: wave.value,
    waveColor: '#1e5aa8',
    progressColor: '#143a6f',
    cursorWidth: 0,
    height: 80,
    barWidth: 2,
    barGap: 1,
  })
  record = ws.registerPlugin(RecordPlugin.create({
    renderRecordedAudio: false,
    scrollingWaveform: true,
  }))
}

async function start() {
  try {
    await ensureOpen()
    recorder.start()
    if (record) await record.startRecording({ deviceId: selectedDeviceId.value || undefined })
  } catch (e) {
    emit('error', (e as Error).message)
  }
}

function stop() {
  if (record) record.stopRecording()
  const result = recorder.stop()
  lastResult.value = result
}

function retake() {
  lastResult.value = null
  ws?.empty()
}

function save() {
  if (lastResult.value) emit('recorded', lastResult.value)
}

watch(selectedDeviceId, async () => {
  if (recorder.state.value !== 'idle') {
    recorder.close()
    ws?.destroy(); ws = null; record = null
  }
})

onBeforeUnmount(() => {
  ws?.destroy(); ws = null; record = null
  recorder.close()
})
</script>

<template>
  <div class="space-y-4">
    <!-- Device picker -->
    <div>
      <label class="label" for="mic">{{ t('record.deviceLabel') }}</label>
      <select id="mic" v-model="selectedDeviceId" class="input">
        <option value="">{{ t('record.selectDevice') }}</option>
        <option v-for="d in devices" :key="d.deviceId" :value="d.deviceId">
          {{ d.label || `Mic ${d.deviceId.slice(0, 6)}` }}
        </option>
      </select>
      <p v-if="!devices.length" class="mt-2 text-xs text-zinc-500">{{ t('record.noDevices') }}</p>
    </div>

    <!-- Waveform -->
    <div class="border border-zinc-200 rounded-lg p-3 bg-zinc-50">
      <div ref="wave" class="w-full h-20" />
    </div>

    <!-- Spectrogram -->
    <SpectrogramCanvas :analyser="recorder.analyser.value" :height="120" />

    <!-- VU -->
    <VuMeter :analyser="recorder.analyser.value" />

    <!-- Controls -->
    <div class="flex flex-wrap gap-2 items-center">
      <button v-if="!isRecording" class="btn-primary" :disabled="recorder.state.value === 'permission'" @click="start">
        <Mic class="w-4 h-4" /> {{ t('record.start') }}
      </button>
      <button v-else class="btn-danger" @click="stop">
        <Square class="w-4 h-4" /> {{ t('record.stop') }}
      </button>

      <button v-if="lastResult" class="btn-secondary" @click="retake">
        <RotateCcw class="w-4 h-4" /> {{ t('record.retake') }}
      </button>
      <button v-if="lastResult" class="btn-primary" @click="save">
        <Save class="w-4 h-4" /> {{ t('record.save') }}
      </button>

      <span v-if="lastResult" class="text-xs text-zinc-600 ml-auto">
        {{ t('record.duration') }}: {{ lastResult.durationS.toFixed(1) }}s
      </span>
    </div>

    <p v-if="recorder.error.value" class="text-sm text-danger-600" role="alert">
      {{ t('record.permissionDenied') }} <span class="text-xs">({{ recorder.error.value }})</span>
    </p>
  </div>
</template>
