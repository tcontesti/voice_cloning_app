<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Mic, Wand2, AudioWaveform, Pencil, Trash2, Plus, Check, X } from 'lucide-vue-next'
import { profilesApi, type Profile } from '@/api/synthesis'
import { recordingsApi, type Recording } from '@/api/recordings'
import LED from '@/ui/primitives/LED.vue'

const { t } = useI18n()

const profiles = ref<Profile[]>([])
const recordings = ref<Recording[]>([])
const loading = ref(false)
const errorMsg = ref<string | null>(null)

// Inline edit state: one profile at a time.
const editingId = ref<string | null>(null)
const editingName = ref('')

// Add-references modal state.
const addingId = ref<string | null>(null)
const addingSelection = ref<Set<string>>(new Set())

// Delete confirm state — single-stage confirm (click twice within 5s) rather
// than a modal, since the action is reversible via recreation.
const pendingDeleteId = ref<string | null>(null)
let pendingDeleteTimer: ReturnType<typeof setTimeout> | null = null

onMounted(async () => {
  loading.value = true
  try {
    const [ps, rs] = await Promise.all([profilesApi.list(), recordingsApi.list()])
    profiles.value = ps.items
    recordings.value = rs.items
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

function startEdit(p: Profile) {
  editingId.value = p.id
  editingName.value = p.name
}

async function commitEdit() {
  const id = editingId.value
  if (!id) return
  const newName = editingName.value.trim()
  const p = profiles.value.find((x) => x.id === id)
  if (!p || !newName || newName === p.name) {
    editingId.value = null
    return
  }
  try {
    const updated = await profilesApi.update(id, { name: newName })
    const idx = profiles.value.findIndex((x) => x.id === id)
    if (idx >= 0) profiles.value[idx] = updated
  } catch (e) {
    errorMsg.value = (e as Error).message
  } finally {
    editingId.value = null
  }
}

function cancelEdit() { editingId.value = null }

function requestDelete(id: string) {
  if (pendingDeleteId.value === id) { void confirmDelete(id); return }
  pendingDeleteId.value = id
  if (pendingDeleteTimer) clearTimeout(pendingDeleteTimer)
  pendingDeleteTimer = setTimeout(() => {
    if (pendingDeleteId.value === id) pendingDeleteId.value = null
  }, 5000)
}

async function confirmDelete(id: string) {
  pendingDeleteId.value = null
  try {
    await profilesApi.remove(id)
    profiles.value = profiles.value.filter((x) => x.id !== id)
  } catch (e) {
    errorMsg.value = (e as Error).message
  }
}

function openAddRefs(p: Profile) {
  addingId.value = p.id
  addingSelection.value = new Set(p.reference_ids)
}

function toggleRef(id: string) {
  const s = new Set(addingSelection.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  addingSelection.value = s
}

async function commitAddRefs() {
  const id = addingId.value
  if (!id) return
  const ids = Array.from(addingSelection.value)
  if (!ids.length) { errorMsg.value = 'Un perfil necesita al menos una referencia.'; return }
  try {
    const updated = await profilesApi.update(id, { reference_ids: ids })
    const idx = profiles.value.findIndex((x) => x.id === id)
    if (idx >= 0) profiles.value[idx] = updated
    addingId.value = null
  } catch (e) {
    errorMsg.value = (e as Error).message
  }
}

function closeAddRefs() { addingId.value = null }
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

        <div class="profiles__name-row">
          <template v-if="editingId === p.id">
            <input
              v-model="editingName"
              class="input profiles__name-input"
              maxlength="128"
              autofocus
              @keydown.enter.prevent="commitEdit"
              @keydown.esc.prevent="cancelEdit"
            />
            <button type="button" class="profiles__icon-btn" aria-label="Guardar" @click="commitEdit">
              <Check class="w-4 h-4" />
            </button>
            <button type="button" class="profiles__icon-btn" aria-label="Cancelar" @click="cancelEdit">
              <X class="w-4 h-4" />
            </button>
          </template>
          <template v-else>
            <h3 class="profiles__name">{{ p.name }}</h3>
            <button type="button" class="profiles__icon-btn" aria-label="Renombrar" @click="startEdit(p)">
              <Pencil class="w-4 h-4" />
            </button>
          </template>
        </div>

        <div class="profiles__meta studio-value">
          {{ p.reference_ids.length }} REFS · {{ p.id.slice(0, 8) }}
        </div>

        <div class="profiles__actions">
          <RouterLink :to="{ name: 'synthesize', query: { profile: p.id } }"
                      class="profiles__btn">
            <Wand2 class="w-4 h-4" /><span>USE</span>
          </RouterLink>
          <button type="button" class="profiles__btn" :title="`${recordings.length} grabaciones disponibles`"
                  @click="openAddRefs(p)">
            <Plus class="w-4 h-4" /><span>REFS</span>
          </button>
          <button
            type="button"
            class="profiles__btn profiles__btn--danger"
            :class="{ 'profiles__btn--confirm': pendingDeleteId === p.id }"
            :aria-label="pendingDeleteId === p.id ? 'Confirmar borrado' : 'Borrar perfil'"
            @click="requestDelete(p.id)"
          >
            <Trash2 class="w-4 h-4" />
            <span>{{ pendingDeleteId === p.id ? 'CONFIRMAR' : 'DELETE' }}</span>
          </button>
        </div>
      </li>
    </ul>

    <div v-if="addingId" class="profiles__modal" role="dialog" aria-modal="true" @click.self="closeAddRefs">
      <div class="profiles__modal-card studio-card">
        <header class="profiles__modal-head">
          <div class="studio-label">REFERENCIAS DEL PERFIL</div>
          <button type="button" class="profiles__icon-btn" aria-label="Cerrar" @click="closeAddRefs">
            <X class="w-4 h-4" />
          </button>
        </header>
        <p class="profiles__modal-hint studio-value">
          Marca las grabaciones que formarán parte del perfil. Mínimo 1.
        </p>
        <ul class="profiles__ref-list">
          <li v-if="!recordings.length" class="profiles__ref-empty">
            No tienes grabaciones. Graba primero desde
            <RouterLink :to="{ name: 'record' }" class="profiles__link">Grabar</RouterLink>.
          </li>
          <li v-for="r in recordings" :key="r.id" class="profiles__ref-item">
            <label>
              <input
                type="checkbox"
                :checked="addingSelection.has(r.id)"
                @change="toggleRef(r.id)"
              />
              <span class="profiles__ref-meta">
                {{ r.duration_s.toFixed(1) }}s
                · SNR {{ r.snr_db?.toFixed(0) ?? '—' }} dB
                · {{ new Date(r.created_at).toLocaleDateString() }}
                · {{ r.id.slice(0, 8) }}
              </span>
            </label>
          </li>
        </ul>
        <footer class="profiles__modal-foot">
          <button type="button" class="profiles__btn" @click="closeAddRefs">Cancelar</button>
          <button type="button" class="profiles__btn profiles__btn--primary"
                  :disabled="!addingSelection.size" @click="commitAddRefs">
            <Check class="w-4 h-4" /><span>APLICAR ({{ addingSelection.size }})</span>
          </button>
        </footer>
      </div>
    </div>
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

.profiles__name-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.profiles__name {
  margin: 0;
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 18px;
  color: var(--fg-0);
  letter-spacing: -0.01em;
  flex: 1;
}
.profiles__name-input {
  flex: 1;
  margin-top: 0;
  font-size: 15px;
}
.profiles__icon-btn {
  width: 30px; height: 30px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-radius: var(--radius-2);
  color: var(--fg-1);
  cursor: pointer;
  transition: color var(--dur-base) var(--ease-studio),
              border-color var(--dur-base) var(--ease-studio);
}
.profiles__icon-btn:hover { color: var(--fg-0); border-color: var(--line-2); }
.profiles__meta { color: var(--fg-2); }

.profiles__actions { display: flex; gap: 8px; margin-top: auto; flex-wrap: wrap; }
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
  cursor: pointer;
  transition: border-color var(--dur-base) var(--ease-studio),
              color var(--dur-base) var(--ease-studio);
}
.profiles__btn:hover:not(:disabled) { border-color: var(--accent); color: var(--accent-glow); }
.profiles__btn:disabled { opacity: 0.4; cursor: not-allowed; }
.profiles__btn--danger:hover { border-color: var(--signal-red); color: var(--signal-red); }
.profiles__btn--confirm {
  background: color-mix(in srgb, var(--signal-red) 20%, var(--bg-2));
  border-color: var(--signal-red);
  color: var(--signal-red);
}
.profiles__btn--primary {
  background: color-mix(in srgb, var(--accent) 20%, var(--bg-2));
  border-color: var(--accent);
}

.profiles__modal {
  position: fixed;
  inset: 0;
  background: color-mix(in srgb, var(--bg-0) 80%, transparent);
  display: grid;
  place-items: center;
  z-index: 50;
  padding: 24px;
}
.profiles__modal-card {
  width: 100%;
  max-width: 560px;
  max-height: min(80vh, 620px);
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 20px;
}
.profiles__modal-head { display: flex; align-items: center; justify-content: space-between; }
.profiles__modal-hint { color: var(--fg-2); margin: 0; }
.profiles__ref-list {
  list-style: none;
  padding: 4px;
  margin: 0;
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 360px;
}
.profiles__ref-empty {
  padding: 16px;
  color: var(--fg-2);
  font-family: var(--font-mono);
  font-size: 12px;
  text-align: center;
}
.profiles__ref-item label {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: var(--radius-2);
  color: var(--fg-0);
  cursor: pointer;
  transition: border-color var(--dur-base) var(--ease-studio);
}
.profiles__ref-item label:hover { border-color: var(--line-2); }
.profiles__ref-meta {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--fg-1);
  letter-spacing: 0.02em;
}
.profiles__modal-foot {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}
.profiles__link { color: var(--accent-glow); }
</style>
