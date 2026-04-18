<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Send, ShieldCheck, ShieldAlert, Download, Sliders, Play, Pause } from 'lucide-vue-next'
import {
  synthesisApi,
  profilesApi,
  type ModelInfo,
  type Profile,
  type SynthesisModel,
  type SynthesisRow,
} from '@/api/synthesis'
import { recordingsApi, type Recording } from '@/api/recordings'
import { useJobProgress } from '@/composables/useJobProgress'
import { ApiError } from '@/api/client'
import ModelCard from '@/ui/composites/ModelCard.vue'
import JobMonitor from '@/ui/composites/JobMonitor.vue'
import OptionsPanel, { type ElevenOptions } from '@/ui/composites/OptionsPanel.vue'
import WaveformTimeline from '@/ui/primitives/WaveformTimeline.vue'
import { useSystemHealth } from '@/composables/useSystemHealth'
import type { WorkerName } from '@/api/system'
import { useAuthStore } from '@/stores/auth'

const { data: health, degraded, workerAvailable } = useSystemHealth()
const auth = useAuthStore()
const route = useRoute()

const { t } = useI18n()

const models = ref<ModelInfo[]>([])
const profiles = ref<Profile[]>([])
const recordings = ref<Recording[]>([])

const text = ref('')
const selectedModel = ref<SynthesisModel>('chatterbox')
const selectedProfileId = ref<string>('')
const selectedRefId = ref<string>('')

const submitting = ref(false)
const errorMsg = ref<string | null>(null)
const job = ref<SynthesisRow | null>(null)
const jobId = computed(() => job.value?.id ?? null)
const { last, connected } = useJobProgress(() => jobId.value)

const optionsOpen = ref(false)
const elevenOptions = ref<ElevenOptions>({
  model_id: 'eleven_multilingual_v2',
  stability: 0.5,
  similarity_boost: 0.85,
  style: 0,
  use_speaker_boost: true,
})

const supportsOptions = computed(() =>
  String(selectedModel.value).toLowerCase().includes('eleven'),
)

const player = ref<HTMLAudioElement | null>(null)
const playing = ref(false)
const playerDuration = ref(0)
const playerTime = ref(0)

onMounted(async () => {
  ;[models.value, profiles.value, recordings.value] = await Promise.all([
    synthesisApi.models(),
    profilesApi.list().then((r) => r.items),
    recordingsApi.list().then((r) => r.items),
  ])
  // ProfilesView USE button links to /synthesize?profile=<id>. Honour it when
  // the profile is still in the list; otherwise fall back to first-available.
  const requested = typeof route.query.profile === 'string' ? route.query.profile : null
  const preselect = requested && profiles.value.find((p) => p.id === requested)
  if (preselect) selectedProfileId.value = preselect.id
  else if (profiles.value.length) selectedProfileId.value = profiles.value[0].id
  const firstAvailable = models.value.find((m) => m.available)
  if (firstAvailable) selectedModel.value = firstAvailable.name as SynthesisModel
})

function selectModel(m: ModelInfo) {
  if (!m.available) return
  selectedModel.value = m.name as SynthesisModel
}

function modelOnline(name: string): boolean {
  // When the health probe hasn't answered yet, assume online so the UI doesn't
  // flash a disabled state during the initial ~10s after mount.
  if (!health.value) return true
  return workerAvailable(name as WorkerName)
}
const selectedModelOnline = computed(() => modelOnline(selectedModel.value))
const submitBlocked = computed(() => {
  if (submitting.value || !text.value.trim()) return true
  if (degraded.value === 'backend-down') return true
  return !selectedModelOnline.value
})
const submitBlockedReason = computed(() => {
  if (degraded.value === 'backend-down') return t('synth.blockedBackend')
  if (!selectedModelOnline.value) return t('synth.blockedSpark')
  return ''
})

async function ensureProfile(): Promise<string> {
  if (selectedProfileId.value) return selectedProfileId.value
  if (!selectedRefId.value) throw new Error('Selecciona una referencia o un perfil existente.')
  const p = await profilesApi.create('Auto', [selectedRefId.value])
  profiles.value.unshift(p)
  selectedProfileId.value = p.id
  return p.id
}

async function submit() {
  errorMsg.value = null
  submitting.value = true
  job.value = null
  try {
    const profile_id = await ensureProfile()
    const body: Parameters<typeof synthesisApi.create>[0] = {
      profile_id,
      model: selectedModel.value,
      text: text.value,
    }
    if (supportsOptions.value) body.options = { ...elevenOptions.value }
    job.value = await synthesisApi.create(body)
  } catch (e) {
    errorMsg.value =
      e instanceof ApiError
        ? typeof e.detail === 'string' ? e.detail : 'Error'
        : (e as Error).message
  } finally {
    submitting.value = false
  }
}

// Audio is served from a Bearer-protected endpoint, but <audio src> and
// WaveSurfer's loader use plain GET without our auth header. We fetch the
// blob ourselves and hand the player an object URL.
const audioUrl = ref<string | null>(null)

watch(
  () => [job.value?.id, last.value?.stage, job.value?.status] as const,
  async ([id, stage, status]) => {
    const ready = !!id && (stage === 'done' || status === 'succeeded')
    if (!ready || !id) {
      if (audioUrl.value) { URL.revokeObjectURL(audioUrl.value); audioUrl.value = null }
      return
    }
    if (audioUrl.value) return  // already loaded for this job
    try {
      const res = await fetch(synthesisApi.audioUrl(id), {
        headers: auth.token ? { Authorization: `Bearer ${auth.token}` } : {},
      })
      if (!res.ok) throw new Error(`audio ${res.status}`)
      const blob = await res.blob()
      audioUrl.value = URL.createObjectURL(blob)
    } catch (e) {
      errorMsg.value = `No se pudo cargar el audio: ${(e as Error).message}`
    }
  },
)

onBeforeUnmount(() => {
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
})

const wmStatus = computed(() => {
  const verified =
    (last.value?.payload as { watermark_verified?: boolean })?.watermark_verified
    ?? job.value?.watermark_verified
  if (verified === true) return 'ok'
  if (verified === false) return 'missing'
  return null
})

const stage = computed(() => last.value?.stage ?? (job.value ? job.value.status : 'idle'))
const pct = computed(() => Math.max(0, last.value?.pct ?? 0))
const finished = computed(() => job.value?.status === 'succeeded' || stage.value === 'done')
const failed = computed(() => job.value?.status === 'failed' || stage.value === 'failed')
const running = computed(() => !!job.value && !finished.value && !failed.value)

function modelMetrics(m: ModelInfo) {
  return [
    { label: 'RTF', value: m.available ? '~0.4' : '—' },
    { label: 'MOS', value: m.available ? '4.1' : '—' },
    { label: 'SIM', value: m.available ? '0.86' : '—' },
  ]
}

function togglePlay() {
  if (!player.value) return
  if (player.value.paused) void player.value.play()
  else player.value.pause()
}

watch(audioUrl, () => {
  playing.value = false
  playerTime.value = 0
  playerDuration.value = 0
})
</script>

<template>
  <div class="synth">
    <header class="synth__header">
      <div>
        <div class="studio-label">SYNTHESIZE</div>
        <h1 class="display-2 synth__title">{{ t('nav.synthesize') }}</h1>
      </div>
      <button
        v-if="supportsOptions"
        type="button"
        class="synth__opts-toggle"
        :class="{ 'synth__opts-toggle--on': optionsOpen }"
        @click="optionsOpen = !optionsOpen"
      >
        <Sliders class="w-4 h-4" /><span>OPTIONS</span>
      </button>
    </header>

    <div class="synth__grid">
      <aside class="synth__models">
        <div class="studio-label synth__section-label">MODELOS</div>
        <div class="synth__model-list">
          <ModelCard
            v-for="m in models"
            :key="m.name"
            :name="m.name"
            :license="m.license"
            :notes="m.notes ?? undefined"
            :selected="selectedModel === (m.name as SynthesisModel)"
            :available="m.available && modelOnline(m.name)"
            :metrics="modelMetrics(m)"
            @select="selectModel(m)"
          />
        </div>

        <Transition name="opts">
          <OptionsPanel
            v-if="supportsOptions && optionsOpen"
            v-model:open="optionsOpen"
            v-model:options="elevenOptions"
          />
        </Transition>
      </aside>

      <section class="synth__main">
        <div class="studio-card synth__inputs">
          <div v-if="profiles.length" class="synth__field">
            <label class="studio-label" for="synth-profile">PERFIL DE VOZ</label>
            <select id="synth-profile" v-model="selectedProfileId" class="input">
              <option v-for="p in profiles" :key="p.id" :value="p.id">
                {{ p.name }} · {{ p.reference_ids.length }} ref
              </option>
            </select>
          </div>
          <div v-else class="synth__field">
            <label class="studio-label" for="synth-ref">REFERENCIA (auto-perfil)</label>
            <select id="synth-ref" v-model="selectedRefId" class="input">
              <option value="">— selecciona referencia —</option>
              <option v-for="r in recordings" :key="r.id" :value="r.id">
                {{ r.duration_s.toFixed(1) }}s · SNR {{ r.snr_db?.toFixed(0) ?? '—' }} dB
              </option>
            </select>
          </div>

          <div class="synth__field">
            <label class="studio-label" for="synth-text">TEXTO</label>
            <textarea
              id="synth-text"
              v-model="text"
              rows="6"
              maxlength="500"
              class="input synth__textarea"
              placeholder="Escribe el texto a sintetizar…"
            />
            <div class="studio-value synth__count">{{ text.length }} / 500</div>
          </div>

          <button
            type="button"
            class="btn btn-primary synth__submit"
            :disabled="submitBlocked"
            :title="submitBlockedReason || undefined"
            @click="submit"
          >
            <Send class="w-4 h-4" />
            {{ submitting ? 'GENERANDO…' : 'GENERATE' }}
          </button>

          <p v-if="submitBlockedReason && !submitting && text.trim()"
             class="synth__warn" role="status">
            {{ submitBlockedReason }}
          </p>
          <p v-if="errorMsg" class="synth__error" role="alert">{{ errorMsg }}</p>
        </div>

        <JobMonitor
          v-if="job"
          :stage="stage"
          :message="last?.message"
          :pct="pct"
          :running="running"
          :finished="finished"
          :failed="failed"
        />

        <div v-if="audioUrl" class="studio-card synth__player">
          <div class="synth__player-head">
            <div class="studio-label">OUTPUT · AUDIO</div>
            <div class="synth__meta">
              <span v-if="wmStatus === 'ok'" class="synth__badge synth__badge--ok">
                <ShieldCheck class="w-4 h-4" /> WM VERIFICADO
              </span>
              <span v-else-if="wmStatus === 'missing'" class="synth__badge synth__badge--err">
                <ShieldAlert class="w-4 h-4" /> WM AUSENTE
              </span>
              <span v-if="job?.aasist_score !== null && job?.aasist_score !== undefined"
                    class="studio-value">
                AASIST {{ job.aasist_score.toFixed(2) }}
              </span>
              <span v-if="job?.rtf !== null && job?.rtf !== undefined" class="studio-value">
                RTF {{ job.rtf.toFixed(2) }}
              </span>
            </div>
          </div>

          <WaveformTimeline :src="audioUrl" :height="120" />

          <div class="synth__player-controls">
            <button type="button" class="synth__pbtn" @click="togglePlay">
              <component :is="playing ? Pause : Play" class="w-4 h-4" />
              <span>{{ playing ? 'PAUSE' : 'PLAY' }}</span>
            </button>
            <a :href="audioUrl" :download="`synthesis-${job?.id.slice(0, 8) ?? 'out'}.wav`"
               class="synth__pbtn">
              <Download class="w-4 h-4" /><span>DOWNLOAD</span>
            </a>
            <span class="studio-value synth__conn">
              WS · {{ connected ? 'connected' : 'idle' }}
            </span>
          </div>

          <audio
            ref="player"
            :src="audioUrl"
            class="synth__audio-hidden"
            @play="playing = true"
            @pause="playing = false"
            @ended="playing = false"
            @loadedmetadata="(e) => (playerDuration = (e.target as HTMLAudioElement).duration)"
            @timeupdate="(e) => (playerTime = (e.target as HTMLAudioElement).currentTime)"
          />
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.synth {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 1440px;
  margin: 0 auto;
}
.synth__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.synth__title { margin: 4px 0 0; color: var(--fg-0); }
.synth__opts-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--fg-1);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: border-color var(--dur-base) var(--ease-studio),
              color var(--dur-base) var(--ease-studio);
}
.synth__opts-toggle:hover { color: var(--fg-0); border-color: var(--line-2); }
.synth__opts-toggle--on {
  color: var(--fg-0);
  border-color: var(--accent);
  box-shadow: 0 0 16px color-mix(in srgb, var(--accent) 30%, transparent);
}

.synth__grid {
  display: grid;
  grid-template-columns: minmax(320px, 380px) 1fr;
  gap: 24px;
  align-items: start;
}
@media (max-width: 960px) {
  .synth__grid { grid-template-columns: 1fr; }
}

.synth__models { display: flex; flex-direction: column; gap: 14px; position: relative; }
.synth__section-label { color: var(--fg-2); }
.synth__model-list { display: flex; flex-direction: column; gap: 12px; }

.synth__main { display: flex; flex-direction: column; gap: 18px; }
.synth__inputs {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.synth__field { display: flex; flex-direction: column; gap: 6px; }
.synth__textarea {
  font-family: var(--font-sans);
  line-height: 1.55;
  resize: vertical;
  min-height: 140px;
}
.synth__count { align-self: flex-end; color: var(--fg-2); }
.synth__submit {
  padding: 14px;
  font-family: var(--font-mono);
  font-size: 13px;
  letter-spacing: 0.12em;
  align-self: stretch;
}
.synth__error {
  margin: 0;
  padding: 10px 14px;
  background: color-mix(in srgb, var(--signal-red) 12%, var(--bg-1));
  border: 1px solid var(--signal-red);
  border-radius: var(--radius-3);
  color: var(--signal-red);
  font-family: var(--font-mono);
  font-size: 12px;
}
.synth__warn {
  margin: 0;
  padding: 10px 14px;
  background: color-mix(in srgb, var(--signal-amber) 10%, var(--bg-1));
  border: 1px solid color-mix(in srgb, var(--signal-amber) 45%, transparent);
  border-radius: var(--radius-3);
  color: var(--signal-amber);
  font-family: var(--font-mono);
  font-size: 12px;
}

.synth__player {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.synth__player-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}
.synth__meta { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.synth__badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--line);
}
.synth__badge--ok { color: var(--signal-green); border-color: color-mix(in srgb, var(--signal-green) 50%, transparent); }
.synth__badge--err { color: var(--signal-red); border-color: color-mix(in srgb, var(--signal-red) 50%, transparent); }

.synth__player-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}
.synth__pbtn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--fg-0);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  cursor: pointer;
  text-decoration: none;
  transition: border-color var(--dur-base) var(--ease-studio),
              transform var(--dur-base) var(--ease-studio);
}
.synth__pbtn:hover { border-color: var(--line-2); transform: translateY(-1px); }
.synth__conn { margin-left: auto; color: var(--fg-2); }
.synth__audio-hidden { display: none; }

.opts-enter-from, .opts-leave-to { opacity: 0; transform: translateX(8px); }
.opts-enter-active, .opts-leave-active {
  transition: opacity var(--dur-base) var(--ease-studio),
              transform var(--dur-base) var(--ease-studio);
}
</style>
