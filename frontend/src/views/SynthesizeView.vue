<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Play, Send, Loader, ShieldCheck, ShieldAlert } from 'lucide-vue-next'
import { synthesisApi, profilesApi, type ModelInfo, type Profile, type SynthesisRow } from '@/api/synthesis'
import { recordingsApi, type Recording } from '@/api/recordings'
import { useJobProgress } from '@/composables/useJobProgress'
import { ApiError } from '@/api/client'

const { t } = useI18n()

const models = ref<ModelInfo[]>([])
const profiles = ref<Profile[]>([])
const recordings = ref<Recording[]>([])

const text = ref('')
const selectedModel = ref<'chatterbox' | 'omnivoice' | 'qwen3tts'>('chatterbox')
const selectedProfileId = ref<string>('')
const selectedRefId = ref<string>('')

const submitting = ref(false)
const errorMsg = ref<string | null>(null)
const job = ref<SynthesisRow | null>(null)
const jobId = computed(() => job.value?.id ?? null)
const { last, connected, events } = useJobProgress(() => jobId.value)

onMounted(async () => {
  ;[models.value, profiles.value, recordings.value] = await Promise.all([
    synthesisApi.models(),
    profilesApi.list().then((r) => r.items),
    recordingsApi.list().then((r) => r.items),
  ])
  if (profiles.value.length) selectedProfileId.value = profiles.value[0].id
})

async function ensureProfile(): Promise<string> {
  if (selectedProfileId.value) return selectedProfileId.value
  if (!selectedRefId.value) throw new Error('seleccione una referencia o un perfil existente')
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
    job.value = await synthesisApi.create({
      profile_id,
      model: selectedModel.value,
      text: text.value,
    })
  } catch (e) {
    errorMsg.value = e instanceof ApiError
      ? (typeof e.detail === 'string' ? e.detail : 'Error')
      : (e as Error).message
  } finally {
    submitting.value = false
  }
}

const audioUrl = computed(() => {
  if (!job.value) return null
  const stage = last.value?.stage
  if (stage !== 'done' && job.value.status !== 'succeeded') return null
  return synthesisApi.audioUrl(job.value.id)
})

const wmStatus = computed(() => {
  const verified = (last.value?.payload as { watermark_verified?: boolean })?.watermark_verified
    ?? job.value?.watermark_verified
  if (verified === true) return 'ok'
  if (verified === false) return 'missing'
  return null
})
</script>

<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <h1 class="text-2xl font-semibold">{{ t('nav.synthesize') }}</h1>

    <div class="card space-y-4">
      <div>
        <label class="label" for="model">Modelo</label>
        <select id="model" v-model="selectedModel" class="input">
          <option v-for="m in models" :key="m.name" :value="m.name" :disabled="!m.available">
            {{ m.name }} — {{ m.license }}{{ m.available ? '' : ' (no disponible)' }}
          </option>
        </select>
      </div>

      <div v-if="profiles.length">
        <label class="label" for="profile">Perfil de voz</label>
        <select id="profile" v-model="selectedProfileId" class="input">
          <option v-for="p in profiles" :key="p.id" :value="p.id">
            {{ p.name }} ({{ p.reference_ids.length }} ref)
          </option>
        </select>
      </div>
      <div v-else>
        <label class="label" for="ref">Grabación de referencia</label>
        <select id="ref" v-model="selectedRefId" class="input">
          <option value="">— selecciona una referencia —</option>
          <option v-for="r in recordings" :key="r.id" :value="r.id">
            {{ r.duration_s.toFixed(1) }}s · SNR {{ r.snr_db?.toFixed(0) ?? '—' }} dB
          </option>
        </select>
        <p class="mt-1 text-xs text-zinc-500">Se creará un perfil automático con esta referencia.</p>
      </div>

      <div>
        <label class="label" for="text">Texto</label>
        <textarea id="text" v-model="text" rows="4" maxlength="500" class="input" />
        <div class="mt-1 text-xs text-zinc-500 text-right">{{ text.length }} / 500</div>
      </div>

      <button class="btn-primary w-full" :disabled="submitting || !text.trim()" @click="submit">
        <Send class="w-4 h-4" /> Generar
      </button>

      <p v-if="errorMsg" class="text-sm text-danger-600" role="alert">{{ errorMsg }}</p>
    </div>

    <div v-if="job" class="card space-y-3">
      <div class="flex items-center gap-3">
        <Loader v-if="!last || (last.stage !== 'done' && last.stage !== 'failed')"
                class="w-4 h-4 animate-spin text-accent-600" />
        <span class="font-medium">
          {{ last?.message ?? job.status }}
          <span v-if="last && last.pct >= 0" class="text-zinc-500 text-sm">· {{ last.pct }}%</span>
        </span>
        <span class="text-xs text-zinc-400 ml-auto">{{ connected ? 'conectado' : 'desconectado' }}</span>
      </div>
      <div class="w-full h-2 rounded-full bg-zinc-200 overflow-hidden">
        <div class="h-full bg-accent-600 transition-[width] duration-200"
             :style="{ width: `${Math.max(0, last?.pct ?? 0)}%` }" />
      </div>

      <div v-if="audioUrl" class="space-y-2 pt-2 border-t border-zinc-100">
        <audio :src="audioUrl" controls class="w-full" />
        <div class="flex flex-wrap items-center gap-3 text-sm">
          <span v-if="wmStatus === 'ok'" class="inline-flex items-center gap-1 text-success-600">
            <ShieldCheck class="w-4 h-4" /> Watermark verificado
          </span>
          <span v-else-if="wmStatus === 'missing'" class="inline-flex items-center gap-1 text-danger-600">
            <ShieldAlert class="w-4 h-4" /> Watermark NO detectado
          </span>
          <a :href="audioUrl" download class="btn-secondary ml-auto">
            <Play class="w-4 h-4" /> Descargar
          </a>
        </div>
      </div>

      <details v-if="events.length" class="text-xs text-zinc-500">
        <summary class="cursor-pointer">eventos ({{ events.length }})</summary>
        <pre class="mt-2 max-h-40 overflow-auto bg-zinc-50 rounded p-2">{{ events.map(e => `${e.stage} ${e.pct}% ${e.message ?? ''}`).join('\n') }}</pre>
      </details>
    </div>
  </div>
</template>
