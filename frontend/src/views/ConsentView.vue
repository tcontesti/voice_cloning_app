<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { consentApi, type ConsentText } from '@/api/consent'
import { ApiError } from '@/api/client'

const { t } = useI18n()
const router = useRouter()

const text = ref<ConsentText | null>(null)
const reachedBottom = ref(false)
const submitting = ref(false)
const message = ref<{ kind: 'ok' | 'error'; text: string } | null>(null)

onMounted(async () => {
  text.value = await consentApi.current()
})

function onScroll(e: Event) {
  const el = e.target as HTMLElement
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 8) reachedBottom.value = true
}

async function accept() {
  if (!text.value) return
  submitting.value = true
  message.value = null
  try {
    await consentApi.accept(text.value.version, text.value.text_hash)
    message.value = { kind: 'ok', text: t('consent.signed') }
    setTimeout(() => router.push({ name: 'record' }), 1200)
  } catch (e) {
    message.value =
      e instanceof ApiError && e.status === 409
        ? { kind: 'error', text: t('consent.drift') }
        : { kind: 'error', text: t('common.error') }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="card max-w-3xl mx-auto space-y-4">
    <div class="flex items-baseline justify-between">
      <h1 class="text-xl font-semibold">{{ t('consent.title') }}</h1>
      <span v-if="text" class="text-xs text-zinc-500">
        {{ t('consent.version') }} {{ text.version }}
      </span>
    </div>

    <p class="text-sm text-zinc-600">{{ t('consent.intro') }}</p>

    <div
      v-if="text"
      class="prose prose-sm max-w-none border border-zinc-200 rounded-lg p-4 h-96 overflow-y-auto bg-zinc-50 whitespace-pre-wrap"
      @scroll="onScroll"
    >{{ text.body_markdown }}</div>

    <p v-if="text && !reachedBottom" class="text-xs text-zinc-500 text-center">
      ↓ {{ t('consent.scrollNotice') }}
    </p>

    <p v-if="text" class="text-xs text-zinc-400 break-all">
      {{ t('consent.hash') }}: {{ text.text_hash }}
    </p>

    <div v-if="message"
         class="text-sm rounded-lg p-3"
         :class="message.kind === 'ok' ? 'bg-green-50 text-success-600' : 'bg-red-50 text-danger-600'"
         role="status">
      {{ message.text }}
    </div>

    <div class="flex justify-end gap-2 pt-2">
      <button class="btn-secondary" @click="router.back()">{{ t('consent.decline') }}</button>
      <button class="btn-primary" :disabled="!reachedBottom || submitting" @click="accept">
        {{ submitting ? t('common.loading') : t('consent.accept') }}
      </button>
    </div>
  </div>
</template>
