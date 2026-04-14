<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import VoiceRecorder from '@/components/VoiceRecorder.vue'
import { recordingsApi, type Recording } from '@/api/recordings'
import { ApiError } from '@/api/client'
import type { RecorderResult } from '@/composables/useRecorder'

const { t } = useI18n()
const uploading = ref(false)
const uploaded = ref<Recording | null>(null)
const errorMsg = ref<string | null>(null)

async function onRecorded(result: RecorderResult) {
  uploading.value = true
  errorMsg.value = null
  try {
    uploaded.value = await recordingsApi.upload(result.blob)
  } catch (e) {
    if (e instanceof ApiError) {
      const detail = (e.detail as string) ?? t('common.error')
      errorMsg.value = detail
    } else {
      errorMsg.value = t('common.error')
    }
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <div>
      <h1 class="text-2xl font-semibold">{{ t('record.title') }}</h1>
      <p class="text-sm text-zinc-500 mt-1">{{ t('record.step', { n: 2 }) }}</p>
    </div>

    <div class="card">
      <h2 class="font-medium mb-3">{{ t('record.phrases.title') }}</h2>
      <p class="text-sm text-zinc-600 mb-4">{{ t('record.phrases.tip') }}</p>
      <VoiceRecorder @recorded="onRecorded" @error="(m) => (errorMsg = m)" />
    </div>

    <div v-if="uploading" class="card text-sm text-zinc-600">{{ t('record.uploading') }}</div>

    <div v-if="uploaded" class="card space-y-2">
      <p class="text-sm text-success-600 font-medium">✓ {{ t('record.uploaded') }}</p>
      <dl class="grid grid-cols-2 gap-y-1 text-sm">
        <dt class="text-zinc-500">{{ t('record.duration') }}</dt>
        <dd>{{ uploaded.duration_s.toFixed(2) }} s</dd>
        <dt class="text-zinc-500">{{ t('record.snr') }}</dt>
        <dd>{{ uploaded.snr_db !== null ? `${uploaded.snr_db.toFixed(1)} dB` : '—' }}</dd>
        <dt class="text-zinc-500">{{ t('record.speechRatio') }}</dt>
        <dd>{{ uploaded.speech_ratio !== null ? `${(uploaded.speech_ratio * 100).toFixed(0)} %` : '—' }}</dd>
      </dl>
    </div>

    <div v-if="errorMsg" class="card text-sm text-danger-600" role="alert">
      {{ errorMsg }}
    </div>
  </div>
</template>
