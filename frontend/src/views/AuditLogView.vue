<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ShieldCheck, ShieldAlert, FileSearch } from 'lucide-vue-next'
import { auditApi, type AuditEntry, type AuditStats, type ChainStatus } from '@/api/audit'

const { t } = useI18n()

const entries = ref<AuditEntry[]>([])
const total = ref(0)
const offset = ref(0)
const limit = 50
const actionPrefix = ref('')
const action = ref('')
const since = ref('')

const stats = ref<AuditStats | null>(null)
const chain = ref<ChainStatus | null>(null)
const loading = ref(false)
const errorMsg = ref<string | null>(null)
const expandedId = ref<number | null>(null)

const topActions = computed(() => {
  if (!stats.value) return [] as [string, number][]
  return Object.entries(stats.value.by_action)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
})

async function refresh() {
  loading.value = true
  errorMsg.value = null
  try {
    const page = await auditApi.logs({
      limit, offset: offset.value,
      action: action.value || undefined,
      action_prefix: actionPrefix.value || undefined,
      since: since.value || undefined,
    })
    entries.value = page.items
    total.value = page.total
  } catch (e) {
    errorMsg.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

async function loadSidebar() {
  try {
    const [s, c] = await Promise.all([auditApi.stats(), auditApi.verify()])
    stats.value = s
    chain.value = c
  } catch (e) {
    errorMsg.value = (e as Error).message
  }
}

function toggle(id: number) {
  expandedId.value = expandedId.value === id ? null : id
}

function next() { offset.value += limit; refresh() }
function prev() { offset.value = Math.max(0, offset.value - limit); refresh() }

function applyFilters() { offset.value = 0; refresh() }

onMounted(async () => { await Promise.all([refresh(), loadSidebar()]) })
</script>

<template>
  <div class="audit">
    <header class="audit__head">
      <FileSearch class="w-5 h-5" aria-hidden="true" />
      <div>
        <div class="studio-label">AUDIT</div>
        <h1 class="display-2 audit__title">{{ t('audit.title') }}</h1>
      </div>
    </header>

    <div class="audit__summary">
      <div class="studio-card audit__stat">
        <span class="studio-label">{{ t('audit.chainIntegrity') }}</span>
        <div v-if="chain" class="audit__chain">
          <ShieldCheck v-if="chain.ok" class="w-5 h-5 audit__chain--ok" />
          <ShieldAlert v-else class="w-5 h-5 audit__chain--err" />
          <span :class="chain.ok ? 'audit__chain--ok' : 'audit__chain--err'" class="audit__chain-label">
            {{ chain.ok ? t('audit.chainOk') : t('audit.chainBroken') }}
          </span>
          <span class="studio-value">· {{ chain.total_entries }} entradas</span>
        </div>
      </div>
      <div class="studio-card audit__stat">
        <span class="studio-label">{{ t('audit.total') }}</span>
        <span class="audit__stat-num">{{ stats?.total ?? '—' }}</span>
      </div>
      <div class="studio-card audit__stat">
        <span class="studio-label">{{ t('audit.topActions') }}</span>
        <ul class="audit__top">
          <li v-for="[k, v] in topActions" :key="k">
            <span class="audit__top-k">{{ k }}</span>
            <span class="audit__top-v">{{ v }}</span>
          </li>
        </ul>
      </div>
    </div>

    <div class="studio-card audit__filters">
      <div class="audit__field">
        <label class="studio-label">{{ t('audit.filters.action') }}</label>
        <input v-model="action" class="input" placeholder="auth.login.ok" />
      </div>
      <div class="audit__field">
        <label class="studio-label">{{ t('audit.filters.prefix') }}</label>
        <input v-model="actionPrefix" class="input" placeholder="synthesis." />
      </div>
      <div class="audit__field">
        <label class="studio-label">{{ t('audit.filters.since') }}</label>
        <input v-model="since" type="datetime-local" class="input" />
      </div>
      <div class="audit__field audit__field--apply">
        <button class="btn btn-primary audit__apply" @click="applyFilters">
          {{ t('audit.filters.apply') }}
        </button>
      </div>
    </div>

    <p v-if="errorMsg" class="audit__error" role="alert">{{ errorMsg }}</p>

    <div class="studio-card audit__table-wrap">
      <table class="audit__table">
        <thead>
          <tr>
            <th class="studio-label">#</th>
            <th class="studio-label">{{ t('audit.action') }}</th>
            <th class="studio-label">{{ t('audit.resource') }}</th>
            <th class="studio-label">{{ t('audit.actor') }}</th>
            <th class="studio-label">{{ t('audit.when') }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <template v-for="e in entries" :key="e.id">
            <tr class="audit__row" @click="toggle(e.id)">
              <td class="audit__idx">{{ e.id }}</td>
              <td class="audit__action">{{ e.action }}</td>
              <td>
                {{ e.resource_type }}
                <span v-if="e.resource_id" class="studio-value">· {{ e.resource_id.slice(0, 8) }}</span>
              </td>
              <td class="studio-value">{{ e.actor_id?.slice(0, 8) ?? '—' }}</td>
              <td class="studio-value">{{ new Date(e.created_at).toLocaleString() }}</td>
              <td class="audit__exp">{{ expandedId === e.id ? '−' : '+' }}</td>
            </tr>
            <tr v-if="expandedId === e.id" class="audit__detail-row">
              <td colspan="6" class="audit__detail">
                <div class="audit__detail-hashes">
                  <div><span class="studio-label">PREV HASH</span> <code>{{ e.prev_hash }}</code></div>
                  <div><span class="studio-label">HASH</span> <code>{{ e.hash }}</code></div>
                </div>
                <pre class="audit__payload">{{ JSON.stringify(e.payload, null, 2) }}</pre>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <p v-if="!loading && !entries.length" class="audit__empty">{{ t('audit.empty') }}</p>
    </div>

    <div class="audit__pager">
      <span class="studio-value">
        {{ offset + 1 }}–{{ Math.min(offset + limit, total) }} / {{ total }}
      </span>
      <div class="audit__pager-btns">
        <button class="btn btn-secondary" :disabled="offset === 0 || loading" @click="prev">←</button>
        <button class="btn btn-secondary" :disabled="offset + limit >= total || loading" @click="next">→</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.audit { display: flex; flex-direction: column; gap: 20px; max-width: 1440px; margin: 0 auto; color: var(--fg-0); font-family: var(--font-mono); }
.audit__head { display: flex; align-items: center; gap: 14px; color: var(--fg-1); font-family: var(--font-sans); }
.audit__title { margin: 2px 0 0; color: var(--fg-0); }

.audit__summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.audit__stat { padding: 16px 18px; display: flex; flex-direction: column; gap: 6px; }
.audit__stat-num { font-family: var(--font-sans); font-weight: 600; font-size: 28px; color: var(--fg-0); }
.audit__chain { display: flex; align-items: center; gap: 8px; }
.audit__chain--ok { color: var(--signal-green); }
.audit__chain--err { color: var(--signal-red); }
.audit__chain-label { font-weight: 600; }
.audit__top { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 3px; }
.audit__top li { display: flex; justify-content: space-between; font-size: 12px; color: var(--fg-1); }
.audit__top-k { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 8px; }
.audit__top-v { color: var(--fg-2); }

.audit__filters { padding: 16px 18px; display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; align-items: end; }
.audit__field { display: flex; flex-direction: column; gap: 4px; }
.audit__field--apply { justify-content: flex-end; }
.audit__apply { font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.1em; padding: 10px 14px; }

.audit__error {
  margin: 0; padding: 10px 14px;
  border-radius: var(--radius-3);
  background: color-mix(in srgb, var(--signal-red) 12%, var(--bg-1));
  border: 1px solid var(--signal-red);
  color: var(--signal-red); font-size: 12px;
}

.audit__table-wrap { padding: 0; overflow-x: auto; }
.audit__table { width: 100%; border-collapse: collapse; font-size: 12px; }
.audit__table thead th {
  text-align: left;
  padding: 12px 20px;
  border-bottom: 1px solid var(--line-2);
  white-space: nowrap;
}
.audit__table tbody td {
  padding: 10px 20px;
  border-top: 1px solid var(--line);
  color: var(--fg-0);
}
.audit__row { cursor: pointer; transition: background var(--dur-base) var(--ease-studio); }
.audit__row:hover td { background: color-mix(in srgb, var(--accent) 6%, transparent); }

.audit__idx { color: var(--fg-2); }
.audit__action { color: var(--accent-glow); }
.audit__exp { color: var(--fg-2); text-align: right; width: 32px; }

.audit__detail-row td { background: var(--bg-2); border-top: none; }
.audit__detail { padding: 14px 20px !important; }
.audit__detail-hashes { display: flex; flex-direction: column; gap: 4px; color: var(--fg-1); font-size: 11px; word-break: break-all; }
.audit__detail-hashes code { color: var(--fg-0); }
.audit__payload {
  margin: 10px 0 0;
  padding: 10px 12px;
  background: var(--bg-0);
  border: 1px solid var(--line);
  border-radius: var(--radius-2);
  color: var(--fg-1);
  font-size: 11px;
  line-height: 1.5;
  overflow-x: auto;
}

.audit__empty { padding: 32px; text-align: center; color: var(--fg-2); font-size: 12px; }

.audit__pager { display: flex; justify-content: space-between; align-items: center; }
.audit__pager-btns { display: flex; gap: 8px; }
</style>
