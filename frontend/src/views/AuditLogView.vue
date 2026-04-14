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
  <div class="space-y-6">
    <div class="flex items-center gap-2">
      <FileSearch class="w-5 h-5 text-accent-600" />
      <h1 class="text-2xl font-semibold">{{ t('audit.title') }}</h1>
    </div>

    <!-- Chain integrity + stats -->
    <div class="grid md:grid-cols-3 gap-3">
      <div class="card">
        <p class="text-xs text-zinc-500 uppercase">{{ t('audit.chainIntegrity') }}</p>
        <div v-if="chain" class="mt-1 flex items-center gap-2">
          <ShieldCheck v-if="chain.ok" class="w-5 h-5 text-success-600" />
          <ShieldAlert v-else class="w-5 h-5 text-danger-600" />
          <span :class="chain.ok ? 'text-success-600' : 'text-danger-600'" class="font-semibold">
            {{ chain.ok ? t('audit.chainOk') : t('audit.chainBroken') }}
          </span>
          <span class="text-sm text-zinc-500">· {{ chain.total_entries }} entradas</span>
        </div>
      </div>
      <div class="card">
        <p class="text-xs text-zinc-500 uppercase">{{ t('audit.total') }}</p>
        <p class="mt-1 text-2xl font-semibold">{{ stats?.total ?? '—' }}</p>
      </div>
      <div class="card">
        <p class="text-xs text-zinc-500 uppercase">{{ t('audit.topActions') }}</p>
        <ul class="mt-1 text-xs text-zinc-600 space-y-0.5">
          <li v-for="[k, v] in topActions" :key="k" class="flex justify-between">
            <span class="truncate">{{ k }}</span>
            <span class="text-zinc-400 ml-2">{{ v }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- Filters -->
    <div class="card grid sm:grid-cols-4 gap-3">
      <div>
        <label class="label">{{ t('audit.filters.action') }}</label>
        <input v-model="action" class="input" placeholder="auth.login.ok" />
      </div>
      <div>
        <label class="label">{{ t('audit.filters.prefix') }}</label>
        <input v-model="actionPrefix" class="input" placeholder="synthesis." />
      </div>
      <div>
        <label class="label">{{ t('audit.filters.since') }}</label>
        <input v-model="since" type="datetime-local" class="input" />
      </div>
      <div class="flex items-end">
        <button class="btn-primary w-full" @click="applyFilters">{{ t('audit.filters.apply') }}</button>
      </div>
    </div>

    <div v-if="errorMsg" class="card text-sm text-danger-600" role="alert">{{ errorMsg }}</div>

    <!-- Log list -->
    <div class="card overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-zinc-500 uppercase">
            <th class="py-2 pr-4">#</th>
            <th class="py-2 pr-4">{{ t('audit.action') }}</th>
            <th class="py-2 pr-4">{{ t('audit.resource') }}</th>
            <th class="py-2 pr-4">{{ t('audit.actor') }}</th>
            <th class="py-2 pr-4">{{ t('audit.when') }}</th>
            <th class="py-2"></th>
          </tr>
        </thead>
        <tbody>
          <template v-for="e in entries" :key="e.id">
            <tr class="border-t border-zinc-100 hover:bg-zinc-50 cursor-pointer" @click="toggle(e.id)">
              <td class="py-2 pr-4 text-zinc-400">{{ e.id }}</td>
              <td class="py-2 pr-4 font-mono text-xs">{{ e.action }}</td>
              <td class="py-2 pr-4 text-zinc-600">{{ e.resource_type }}<span v-if="e.resource_id" class="text-zinc-400"> · {{ e.resource_id.slice(0, 8) }}</span></td>
              <td class="py-2 pr-4 text-zinc-500">{{ e.actor_id?.slice(0, 8) ?? '—' }}</td>
              <td class="py-2 pr-4 text-zinc-500 whitespace-nowrap">{{ new Date(e.created_at).toLocaleString() }}</td>
              <td class="py-2 text-zinc-400">{{ expandedId === e.id ? '−' : '+' }}</td>
            </tr>
            <tr v-if="expandedId === e.id" class="bg-zinc-50">
              <td colspan="6" class="py-3 px-4">
                <div class="text-xs text-zinc-500 space-y-1 font-mono">
                  <div><span class="text-zinc-400">prev_hash:</span> {{ e.prev_hash }}</div>
                  <div><span class="text-zinc-400">hash:</span> {{ e.hash }}</div>
                </div>
                <pre class="mt-2 text-xs bg-white rounded border border-zinc-200 p-2 overflow-auto">{{ JSON.stringify(e.payload, null, 2) }}</pre>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <p v-if="!loading && !entries.length" class="text-sm text-zinc-500 py-4 text-center">
        {{ t('audit.empty') }}
      </p>
    </div>

    <div class="flex items-center justify-between text-sm">
      <span class="text-zinc-500">
        {{ offset + 1 }}–{{ Math.min(offset + limit, total) }} / {{ total }}
      </span>
      <div class="flex gap-2">
        <button class="btn-secondary" :disabled="offset === 0 || loading" @click="prev">←</button>
        <button class="btn-secondary" :disabled="offset + limit >= total || loading" @click="next">→</button>
      </div>
    </div>
  </div>
</template>
