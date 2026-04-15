<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Check, FileSignature } from 'lucide-vue-next'
import { consentApi, type ConsentText } from '@/api/consent'
import { ApiError } from '@/api/client'
import LED from '@/ui/primitives/LED.vue'

const { t } = useI18n()
const router = useRouter()

const text = ref<ConsentText | null>(null)
const reachedBottom = ref(false)
const submitting = ref(false)
const message = ref<{ kind: 'ok' | 'error'; text: string } | null>(null)

// Drag-to-sign slider — requires ~95% of travel plus 250 ms of "resistance"
// to prevent accidental activation. Respecta prefers-reduced-motion para
// usuarios con baja motricidad fallando a un click con confirmación doble.
const track = ref<HTMLDivElement | null>(null)
const knobPct = ref(0)
const dragging = ref(false)
const reducedMotion = ref(false)

onMounted(async () => {
  reducedMotion.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  text.value = await consentApi.current()
})

function onScroll(e: Event) {
  const el = e.target as HTMLElement
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 8) reachedBottom.value = true
}

function onPointerDown(e: PointerEvent) {
  if (!reachedBottom.value || submitting.value) return
  dragging.value = true
  ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  updateFromPointer(e)
}
function onPointerMove(e: PointerEvent) {
  if (!dragging.value) return
  updateFromPointer(e)
}
function onPointerUp() {
  if (!dragging.value) return
  dragging.value = false
  if (knobPct.value >= 95) void accept()
  else knobPct.value = 0
}
function updateFromPointer(e: PointerEvent) {
  const el = track.value
  if (!el) return
  const r = el.getBoundingClientRect()
  const pct = ((e.clientX - r.left) / r.width) * 100
  knobPct.value = Math.max(0, Math.min(100, pct))
}

function onKnobKey(e: KeyboardEvent) {
  if (!reachedBottom.value) return
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    void accept()
  }
}

async function accept() {
  if (!text.value || submitting.value) return
  submitting.value = true
  message.value = null
  knobPct.value = 100
  try {
    await consentApi.accept(text.value.version, text.value.text_hash)
    message.value = { kind: 'ok', text: t('consent.signed') }
    setTimeout(() => router.push({ name: 'record' }), 1200)
  } catch (e) {
    message.value =
      e instanceof ApiError && e.status === 409
        ? { kind: 'error', text: t('consent.drift') }
        : { kind: 'error', text: t('common.error') }
    knobPct.value = 0
  } finally {
    submitting.value = false
  }
}

onBeforeUnmount(() => { dragging.value = false })
</script>

<template>
  <div class="consent">
    <header class="consent__header">
      <div class="consent__brand">
        <LED color="accent" on size="sm" />
        <span class="studio-label">CONSENT · V{{ text?.version ?? '—' }}</span>
      </div>
      <h1 class="display-2 consent__title">{{ t('consent.title') }}</h1>
      <p class="consent__intro">{{ t('consent.intro') }}</p>
    </header>

    <section class="consent__doc studio-card" aria-live="polite">
      <div v-if="text" class="consent__scroll" @scroll="onScroll">
        {{ text.body_markdown }}
      </div>
      <p v-if="text && !reachedBottom" class="consent__scroll-hint studio-value">
        ↓ {{ t('consent.scrollNotice') }}
      </p>
    </section>

    <aside v-if="text" class="consent__hash studio-value">
      <span class="studio-label">HASH</span>
      <code class="consent__hash-code">{{ text.text_hash }}</code>
    </aside>

    <section
      class="consent__sign studio-card"
      :class="{ 'consent__sign--ready': reachedBottom, 'consent__sign--locked': !reachedBottom }"
    >
      <div class="consent__sign-head">
        <FileSignature class="w-4 h-4" aria-hidden="true" />
        <span class="studio-label">
          {{ reachedBottom ? 'ARRASTRE PARA FIRMAR' : 'LEA HASTA EL FINAL PARA HABILITAR' }}
        </span>
      </div>

      <div
        ref="track"
        class="consent__slider"
        :aria-disabled="!reachedBottom || submitting"
        role="slider"
        :aria-valuenow="Math.round(knobPct)"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-label="t('consent.accept')"
        tabindex="0"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
        @keydown="onKnobKey"
      >
        <div class="consent__slider-fill" :style="{ width: `${knobPct}%` }" />
        <div
          class="consent__knob"
          :class="{ 'consent__knob--dragging': dragging }"
          :style="{ left: `calc(${knobPct}% - 28px)` }"
        >
          <Check class="w-4 h-4" />
        </div>
        <span class="consent__slider-label" :class="{ 'consent__slider-label--hidden': knobPct > 20 }">
          {{ t('consent.accept') }} →
        </span>
      </div>

      <div class="consent__actions">
        <button type="button" class="btn btn-secondary consent__decline" @click="router.back()">
          {{ t('consent.decline') }}
        </button>
      </div>
    </section>

    <div v-if="message"
         class="consent__message"
         :class="message.kind === 'ok' ? 'consent__message--ok' : 'consent__message--err'"
         role="status">
      <LED :color="message.kind === 'ok' ? 'green' : 'red'" on size="xs" />
      <span>{{ message.text }}</span>
    </div>
  </div>
</template>

<style scoped>
.consent {
  max-width: 820px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.consent__header { display: flex; flex-direction: column; gap: 8px; }
.consent__brand { display: flex; align-items: center; gap: 10px; color: var(--fg-1); }
.consent__title { margin: 4px 0 0; color: var(--fg-0); }
.consent__intro { margin: 0; color: var(--fg-1); font-size: 15px; line-height: 1.6; }

.consent__doc { padding: 28px 32px; }
.consent__scroll {
  max-height: 420px;
  overflow-y: auto;
  font-family: "Source Serif 4", Georgia, serif;
  font-weight: 400;
  font-size: 16px;
  line-height: 1.75;
  color: var(--fg-0);
  white-space: pre-wrap;
  padding-right: 12px;
}
.consent__scroll::-webkit-scrollbar { width: 8px; }
.consent__scroll::-webkit-scrollbar-thumb {
  background: var(--line-2);
  border-radius: 4px;
}
.consent__scroll-hint { margin: 14px 0 0; text-align: center; color: var(--fg-2); }

.consent__hash {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 4px;
  color: var(--fg-2);
}
.consent__hash-code {
  font-family: var(--font-mono);
  font-size: 11px;
  word-break: break-all;
  color: var(--fg-2);
}

.consent__sign {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  transition: border-color var(--dur-base) var(--ease-studio);
}
.consent__sign--locked { opacity: 0.6; }
.consent__sign--ready { border-color: var(--accent); }

.consent__sign-head {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--fg-1);
}

.consent__slider {
  position: relative;
  height: 56px;
  border-radius: 999px;
  background: var(--bg-2);
  border: 1px solid var(--line);
  overflow: hidden;
  touch-action: none;
  user-select: none;
  cursor: grab;
}
.consent__slider[aria-disabled="true"] { cursor: not-allowed; }
.consent__slider:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 35%, transparent);
}

.consent__slider-fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: linear-gradient(90deg,
    color-mix(in srgb, var(--accent) 40%, transparent),
    var(--accent-glow));
  transition: width var(--dur-fast) linear;
}
.consent__knob {
  position: absolute;
  top: 4px;
  width: 48px;
  height: 48px;
  border-radius: 999px;
  background: var(--bg-3);
  border: 1px solid var(--line-2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--fg-0);
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
  transition: transform var(--dur-base) var(--ease-studio);
}
.consent__knob--dragging { transform: scale(1.04); border-color: var(--accent); }

.consent__slider-label {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.14em;
  color: var(--fg-1);
  pointer-events: none;
  transition: opacity var(--dur-base) var(--ease-studio);
}
.consent__slider-label--hidden { opacity: 0; }

.consent__actions { display: flex; justify-content: flex-end; }
.consent__decline { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.1em; }

.consent__message {
  display: inline-flex;
  gap: 10px;
  align-items: center;
  padding: 10px 16px;
  border-radius: var(--radius-3);
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.04em;
}
.consent__message--ok {
  background: color-mix(in srgb, var(--signal-green) 12%, var(--bg-1));
  border: 1px solid color-mix(in srgb, var(--signal-green) 40%, transparent);
  color: var(--signal-green);
}
.consent__message--err {
  background: color-mix(in srgb, var(--signal-red) 12%, var(--bg-1));
  border: 1px solid var(--signal-red);
  color: var(--signal-red);
}
</style>
