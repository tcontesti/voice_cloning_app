<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Mic, Wand2, AudioWaveform } from 'lucide-vue-next'
import { profilesApi, type Profile } from '@/api/synthesis'
import LED from '@/ui/primitives/LED.vue'

const { t } = useI18n()

const profiles = ref<Profile[]>([])
const loading = ref(false)
const errorMsg = ref<string | null>(null)

onMounted(async () => {
  loading.value = true
  try {
    profiles.value = (await profilesApi.list()).items
  } catch (e) {
    errorMsg.value = (e as Error).message
  } finally {
    loading.value = false
  }
})

function statusColor(s: Profile['status']): 'green' | 'amber' | 'red' {
  if (s === 'ready') return 'green'
  if (s === 'pending') return 'amber'
  return 'red'
}

function fakeWave(id: string): number[] {
  // Deterministic pseudo-waveform for thumbnails (no real audio fetched here).
  const bars = 48
  let seed = 0
  for (let i = 0; i < id.length; i++) seed = (seed * 31 + id.charCodeAt(i)) >>> 0
  const out: number[] = []
  for (let i = 0; i < bars; i++) {
    seed = (seed * 1103515245 + 12345) >>> 0
    const base = ((seed >>> 16) & 0xff) / 255
    const env = Math.sin((i / bars) * Math.PI)
    out.push(Math.max(0.12, base * env))
  }
  return out
}

const sorted = computed(() =>
  [...profiles.value].sort((a, b) => b.created_at.localeCompare(a.created_at)),
)
</script>

<template>
  <div class="profiles">
    <header class="profiles__head">
      <div>
        <div class="studio-label">PROFILES</div>
        <h1 class="display-2 profiles__title">{{ t('nav.profiles') ?? 'Perfiles de voz' }}</h1>
      </div>
      <RouterLink :to="{ name: 'record' }" class="btn btn-primary profiles__cta">
        <Mic class="w-4 h-4" /><span>NEW PROFILE</span>
      </RouterLink>
    </header>

    <p v-if="errorMsg" class="profiles__error" role="alert">{{ errorMsg }}</p>

    <div v-if="!sorted.length && !loading" class="profiles__empty studio-card">
      <AudioWaveform class="w-8 h-8" aria-hidden="true" />
      <p>Aún no has creado ningún perfil de voz.</p>
      <RouterLink :to="{ name: 'record' }" class="btn btn-primary">
        <Mic class="w-4 h-4" /> Grabar primera referencia
      </RouterLink>
    </div>

    <ul v-else class="profiles__grid">
      <li v-for="p in sorted" :key="p.id" class="profiles__card studio-card">
        <header class="profiles__card-head">
          <LED :color="statusColor(p.status)" on :pulse="p.status === 'pending'" size="sm" />
          <span class="studio-label">{{ p.status.toUpperCase() }}</span>
          <span class="studio-value profiles__date">
            {{ new Date(p.created_at).toLocaleDateString() }}
          </span>
        </header>

        <div class="profiles__wave" aria-hidden="true">
          <span v-for="(h, i) in fakeWave(p.id)" :key="i"
                class="profiles__bar" :style="{ height: `${Math.round(h * 100)}%` }" />
        </div>

        <h3 class="profiles__name">{{ p.name }}</h3>
        <div class="profiles__meta studio-value">
          {{ p.reference_ids.length }} REFS · {{ p.id.slice(0, 8) }}
        </div>

        <div class="profiles__actions">
          <RouterLink :to="{ name: 'synthesize', query: { profile: p.id } }"
                      class="profiles__btn">
            <Wand2 class="w-4 h-4" /><span>USE</span>
          </RouterLink>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.profiles { display: flex; flex-direction: column; gap: 24px; max-width: 1440px; margin: 0 auto; }
.profiles__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}
.profiles__title { margin: 4px 0 0; color: var(--fg-0); }
.profiles__cta {
  padding: 10px 18px;
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.1em;
}
.profiles__error {
  margin: 0;
  padding: 10px 14px;
  border-radius: var(--radius-3);
  background: color-mix(in srgb, var(--signal-red) 12%, var(--bg-1));
  border: 1px solid var(--signal-red);
  color: var(--signal-red);
  font-family: var(--font-mono);
  font-size: 12px;
}
.profiles__empty {
  padding: 48px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  color: var(--fg-2);
  text-align: center;
}

.profiles__grid {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.profiles__card {
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: transform var(--dur-base) var(--ease-studio),
              border-color var(--dur-base) var(--ease-studio),
              box-shadow var(--dur-base) var(--ease-studio);
}
.profiles__card:hover {
  transform: translateY(-2px);
  border-color: var(--line-2);
  box-shadow:
    var(--shadow-card),
    0 0 0 1px color-mix(in srgb, var(--accent) 40%, transparent);
}

.profiles__card-head { display: flex; align-items: center; gap: 8px; }
.profiles__date { margin-left: auto; color: var(--fg-2); }

.profiles__wave {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 56px;
  padding: 4px;
  background: var(--meter-bg);
  border: 1px solid var(--line);
  border-radius: var(--radius-2);
}
.profiles__bar {
  flex: 1;
  min-width: 2px;
  background: linear-gradient(180deg, var(--accent-glow), var(--accent));
  border-radius: 1px;
  opacity: 0.85;
}

.profiles__name {
  margin: 0;
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 18px;
  color: var(--fg-0);
  letter-spacing: -0.01em;
}
.profiles__meta { color: var(--fg-2); }

.profiles__actions { display: flex; gap: 8px; margin-top: auto; }
.profiles__btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--fg-0);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-decoration: none;
  transition: border-color var(--dur-base) var(--ease-studio);
}
.profiles__btn:hover { border-color: var(--accent); color: var(--accent-glow); }
</style>
