<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Users, CheckCircle2, XCircle } from 'lucide-vue-next'
import { adminApi, setUserActive, type AdminUser, type SystemStats } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const auth = useAuthStore()

const users = ref<AdminUser[]>([])
const stats = ref<SystemStats | null>(null)
const loading = ref(false)
const errorMsg = ref<string | null>(null)

async function refresh() {
  loading.value = true
  errorMsg.value = null
  try {
    const [us, st] = await Promise.all([adminApi.users(), adminApi.stats()])
    users.value = us.items
    stats.value = st
  } catch (e) {
    errorMsg.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

async function toggle(u: AdminUser) {
  if (u.id === auth.user?.id) return
  try {
    await setUserActive(u.id, !u.active)
    const idx = users.value.findIndex((x) => x.id === u.id)
    if (idx >= 0) users.value[idx] = { ...users.value[idx], active: !u.active }
  } catch (e) {
    errorMsg.value = (e as Error).message
  }
}

onMounted(refresh)
</script>

<template>
  <div class="admin">
    <header class="admin__head">
      <Users class="w-5 h-5" aria-hidden="true" />
      <div>
        <div class="studio-label">ADMIN</div>
        <h1 class="display-2 admin__title">{{ t('admin.usersTitle') }}</h1>
      </div>
    </header>

    <div v-if="stats" class="admin__stats">
      <div class="studio-card admin__stat">
        <span class="studio-label">{{ t('admin.users') }}</span>
        <span class="admin__stat-num">
          {{ stats.users_active }}
          <span class="admin__stat-sub">/ {{ stats.users_total }}</span>
        </span>
      </div>
      <div class="studio-card admin__stat">
        <span class="studio-label">{{ t('admin.recordings') }}</span>
        <span class="admin__stat-num">
          {{ stats.recordings_active }}
          <span class="admin__stat-sub">/ {{ stats.recordings_total }}</span>
        </span>
      </div>
      <div class="studio-card admin__stat">
        <span class="studio-label">{{ t('admin.syntheses') }}</span>
        <span class="admin__stat-num">{{ stats.syntheses_total }}</span>
        <span class="admin__stat-details studio-value">
          <span v-for="(count, k) in stats.syntheses_by_status" :key="k">
            {{ k }}: {{ count }}
          </span>
        </span>
      </div>
    </div>

    <p v-if="errorMsg" class="admin__error" role="alert">{{ errorMsg }}</p>

    <div class="studio-card admin__table-wrap">
      <table class="admin__table">
        <thead>
          <tr>
            <th class="studio-label">Email</th>
            <th class="studio-label">{{ t('admin.role') }}</th>
            <th class="studio-label">{{ t('admin.created') }}</th>
            <th class="studio-label">{{ t('admin.status') }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>
              <div class="admin__email">{{ u.email }}</div>
              <div class="admin__name studio-value">{{ u.full_name ?? '—' }}</div>
            </td>
            <td>
              <span class="admin__role">{{ u.role }}</span>
            </td>
            <td class="studio-value">{{ new Date(u.created_at).toLocaleDateString() }}</td>
            <td>
              <span v-if="u.active" class="admin__status admin__status--active">
                <CheckCircle2 class="w-4 h-4" /> {{ t('admin.active') }}
              </span>
              <span v-else class="admin__status admin__status--inactive">
                <XCircle class="w-4 h-4" /> {{ t('admin.inactive') }}
              </span>
            </td>
            <td class="admin__td-action">
              <button
                class="btn btn-secondary"
                :disabled="u.id === auth.user?.id"
                :title="u.id === auth.user?.id ? t('admin.cannotSelf') : ''"
                @click="toggle(u)"
              >
                {{ u.active ? t('admin.deactivate') : t('admin.activate') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!loading && !users.length" class="admin__empty">{{ t('admin.noUsers') }}</p>
    </div>
  </div>
</template>

<style scoped>
.admin { display: flex; flex-direction: column; gap: 24px; max-width: 1440px; margin: 0 auto; color: var(--fg-0); }
.admin__head { display: flex; align-items: center; gap: 14px; color: var(--fg-1); }
.admin__title { margin: 2px 0 0; color: var(--fg-0); }

.admin__stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.admin__stat { padding: 16px 18px; display: flex; flex-direction: column; gap: 4px; }
.admin__stat-num {
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 28px;
  color: var(--fg-0);
}
.admin__stat-sub { color: var(--fg-2); font-size: 16px; font-weight: 400; }
.admin__stat-details { display: flex; gap: 10px; flex-wrap: wrap; color: var(--fg-2); margin-top: 2px; }

.admin__error {
  margin: 0; padding: 10px 14px;
  border-radius: var(--radius-3);
  background: color-mix(in srgb, var(--signal-red) 12%, var(--bg-1));
  border: 1px solid var(--signal-red);
  color: var(--signal-red);
  font-family: var(--font-mono); font-size: 12px;
}

.admin__table-wrap { padding: 0; overflow-x: auto; }
.admin__table { width: 100%; border-collapse: collapse; font-size: 14px; }
.admin__table thead th {
  text-align: left;
  padding: 14px 20px;
  border-bottom: 1px solid var(--line-2);
}
.admin__table tbody td {
  padding: 12px 20px;
  border-top: 1px solid var(--line);
  color: var(--fg-0);
  vertical-align: middle;
}
.admin__table tbody tr:hover td { background: color-mix(in srgb, var(--accent) 6%, transparent); }

.admin__email { color: var(--fg-0); }
.admin__name { color: var(--fg-2); margin-top: 2px; }
.admin__role {
  display: inline-block;
  padding: 2px 10px;
  font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.08em;
  border: 1px solid var(--line); border-radius: 999px; color: var(--fg-1);
}
.admin__status { display: inline-flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.08em; }
.admin__status--active   { color: var(--signal-green); }
.admin__status--inactive { color: var(--signal-red); }

.admin__td-action { text-align: right; }
.admin__empty { padding: 32px; text-align: center; color: var(--fg-2); font-family: var(--font-mono); font-size: 12px; }
</style>
