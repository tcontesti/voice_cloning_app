<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Play, Download, ShieldCheck, ShieldAlert } from 'lucide-vue-next'
import { synthesisApi, type SynthesisRow } from '@/api/synthesis'

const { t } = useI18n()

const rows = ref<SynthesisRow[]>([])
const loading = ref(false)
const errorMsg = ref<string | null>(null)
const modelFilter = ref<'all' | SynthesisRow['model']>('all')
const playingId = ref<string | null>(null)

onMounted(async () => {
  loading.value = true
  try {
    rows.value = (await synthesisApi.list()).items
  } catch (e) {
    errorMsg.value = (e as Error).message
  } finally {
    loading.value = false
  }
})

const filtered = computed(() => {
  const base = modelFilter.value === 'all'
    ? rows.value
    : rows.value.filter((r) => r.model === modelFilter.value)
  return [...base].sort((a, b) => b.created_at.localeCompare(a.created_at))
})

function fmtDuration(s: number | null): string {
  if (s === null) return '—'
  const m = Math.floor(s / 60)
  const sec = (s % 60).toFixed(1)
  return `${String(m).padStart(2, '0')}:${sec.padStart(4, '0')}`
}
function fmtTimecode(iso: string): string {
  return new Date(iso).toLocaleString()
}
function statusClass(s: SynthesisRow['status']): string {
  return `hist__status hist__status--${s}`
}
function togglePlay(id: string) {
  playingId.value = playingId.value === id ? null : id
}
</script>

<template>
  <div class="hist">
    <header class="hist__head">
      <div>
        <div class="studio-label">HISTORY</div>
        <h1 class="display-2 hist__title">{{ t('nav.history') }}</h1>
      </div>
      <div class="hist__filter">
        <label class="studio-label" for="hist-model">MODELO</label>
        <select id="hist-model" v-model="modelFilter" class="input hist__select">
          <option value="all">Todos</option>
          <option value="chatterbox">chatterbox</option>
          <option value="omnivoice">omnivoice</option>
          <option value="qwen3tts">qwen3tts</option>
        </select>
      </div>
    </header>

    <p v-if="errorMsg" class="hist__error" role="alert">{{ errorMsg }}</p>

    <section class="hist__table studio-card" role="table">
      <div class="hist__row hist__row--head" role="row">
        <span class="studio-label">#</span>
        <span class="studio-label">FECHA</span>
        <span class="studio-label">TEXTO</span>
        <span class="studio-label">MODELO</span>
        <span class="studio-label">DUR</span>
        <span class="studio-label">RTF</span>
        <span class="studio-label">WM</span>
        <span class="studio-label">ESTADO</span>
        <span class="studio-label"></span>
      </div>

      <div v-if="!filtered.length && !loading" class="hist__empty">
        Aún no hay síntesis. Genera una desde
        <RouterLink :to="{ name: 'synthesize' }" class="hist__link">Sintetizar</RouterLink>.
      </div>

      <template v-else>
        <div v-for="(r, i) in filtered" :key="r.id" class="hist__row" role="row">
          <span class="studio-value hist__idx">{{ String(i + 1).padStart(3, '0') }}</span>
          <span class="studio-value hist__date">{{ fmtTimecode(r.created_at) }}</span>
          <span class="hist__text" :title="r.text">{{ r.text }}</span>
          <span class="hist__model">{{ r.model }}</span>
          <span class="studio-value">{{ fmtDuration(r.duration_s) }}</span>
          <span class="studio-value">{{ r.rtf?.toFixed(2) ?? '—' }}</span>
          <span class="hist__wm">
            <ShieldCheck v-if="r.watermark_verified === true" class="w-4 h-4 hist__wm--ok" />
            <ShieldAlert v-else-if="r.watermark_verified === false" class="w-4 h-4 hist__wm--err" />
            <span v-else class="studio-value">—</span>
          </span>
          <span :class="statusClass(r.status)">{{ r.status }}</span>
          <span class="hist__actions">
            <button
              v-if="r.status === 'succeeded'"
              type="button"
              class="hist__icon-btn"
              :class="{ 'hist__icon-btn--active': playingId === r.id }"
              :aria-label="t('common.play') ?? 'Reproducir'"
              @click="togglePlay(r.id)"
            >
              <Play class="w-4 h-4" />
            </button>
            <a
              v-if="r.status === 'succeeded'"
              :href="synthesisApi.audioUrl(r.id)"
              download
              class="hist__icon-btn"
              :aria-label="t('common.download') ?? 'Descargar'"
            >
              <Download class="w-4 h-4" />
            </a>
          </span>
          <audio v-if="playingId === r.id" :src="synthesisApi.audioUrl(r.id)"
                 class="hist__audio" autoplay controls @ended="playingId = null" />
        </div>
      </template>
    </section>
  </div>
</template>

<style scoped>
.hist { display: flex; flex-direction: column; gap: 20px; max-width: 1440px; margin: 0 auto; }
.hist__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}
.hist__title { margin: 4px 0 0; color: var(--fg-0); }
.hist__filter { display: flex; flex-direction: column; gap: 4px; }
.hist__select { margin-top: 0; min-width: 180px; }

.hist__error {
  margin: 0;
  padding: 10px 14px;
  border-radius: var(--radius-3);
  background: color-mix(in srgb, var(--signal-red) 12%, var(--bg-1));
  border: 1px solid var(--signal-red);
  color: var(--signal-red);
  font-family: var(--font-mono);
  font-size: 12px;
}

.hist__table {
  padding: 8px 0;
  overflow-x: auto;
}
.hist__row {
  display: grid;
  grid-template-columns: 48px 170px 1fr 110px 70px 60px 36px 90px 90px;
  gap: 12px;
  padding: 12px 20px;
  align-items: center;
  min-height: 48px;
  border-bottom: 1px solid var(--line);
  transition: background var(--dur-base) var(--ease-studio);
}
.hist__row:last-child { border-bottom: none; }
.hist__row:not(.hist__row--head):hover { background: color-mix(in srgb, var(--accent) 6%, transparent); }

.hist__row--head {
  border-bottom: 1px solid var(--line-2);
  min-height: 36px;
  padding-top: 8px;
  padding-bottom: 8px;
}

.hist__idx, .hist__date { color: var(--fg-2); }
.hist__text {
  color: var(--fg-0);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.hist__model {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
  padding: 3px 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  justify-self: start;
  color: var(--fg-1);
}
.hist__wm { display: inline-flex; align-items: center; justify-content: center; }
.hist__wm--ok { color: var(--signal-green); }
.hist__wm--err { color: var(--signal-red); }

.hist__status {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  padding: 3px 8px;
  border-radius: 999px;
  justify-self: start;
  border: 1px solid var(--line);
  text-transform: uppercase;
}
.hist__status--succeeded { color: var(--signal-green); border-color: color-mix(in srgb, var(--signal-green) 50%, transparent); }
.hist__status--failed    { color: var(--signal-red);   border-color: color-mix(in srgb, var(--signal-red) 50%, transparent); }
.hist__status--running   { color: var(--signal-amber); border-color: color-mix(in srgb, var(--signal-amber) 50%, transparent); }
.hist__status--queued    { color: var(--signal-blue);  border-color: color-mix(in srgb, var(--signal-blue) 50%, transparent); }

.hist__actions { display: flex; gap: 6px; justify-self: end; }
.hist__icon-btn {
  width: 30px; height: 30px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-radius: var(--radius-2);
  color: var(--fg-1);
  cursor: pointer;
  text-decoration: none;
  transition: color var(--dur-base) var(--ease-studio),
              border-color var(--dur-base) var(--ease-studio);
}
.hist__icon-btn:hover { color: var(--fg-0); border-color: var(--line-2); }
.hist__icon-btn--active { color: var(--accent-glow); border-color: var(--accent); }

.hist__audio {
  grid-column: 1 / -1;
  width: 100%;
  margin-top: 8px;
}

.hist__empty {
  padding: 48px;
  text-align: center;
  color: var(--fg-2);
  font-family: var(--font-mono);
  font-size: 12px;
}
.hist__link { color: var(--accent-glow); }
</style>
