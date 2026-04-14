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
  <div class="space-y-6">
    <div class="flex items-center gap-2">
      <Users class="w-5 h-5 text-accent-600" />
      <h1 class="text-2xl font-semibold">{{ t('admin.usersTitle') }}</h1>
    </div>

    <div v-if="stats" class="grid sm:grid-cols-3 gap-3">
      <div class="card">
        <p class="text-xs text-zinc-500 uppercase">{{ t('admin.users') }}</p>
        <p class="mt-1 text-2xl font-semibold">{{ stats.users_active }} <span class="text-base text-zinc-400">/ {{ stats.users_total }}</span></p>
      </div>
      <div class="card">
        <p class="text-xs text-zinc-500 uppercase">{{ t('admin.recordings') }}</p>
        <p class="mt-1 text-2xl font-semibold">{{ stats.recordings_active }} <span class="text-base text-zinc-400">/ {{ stats.recordings_total }}</span></p>
      </div>
      <div class="card">
        <p class="text-xs text-zinc-500 uppercase">{{ t('admin.syntheses') }}</p>
        <p class="mt-1 text-2xl font-semibold">{{ stats.syntheses_total }}</p>
        <p class="mt-1 text-xs text-zinc-500">
          <span v-for="(count, k) in stats.syntheses_by_status" :key="k" class="mr-2">
            {{ k }}: {{ count }}
          </span>
        </p>
      </div>
    </div>

    <div v-if="errorMsg" class="card text-sm text-danger-600" role="alert">{{ errorMsg }}</div>

    <div class="card overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead>
          <tr class="text-left text-xs text-zinc-500 uppercase">
            <th class="py-2 pr-4">Email</th>
            <th class="py-2 pr-4">{{ t('admin.role') }}</th>
            <th class="py-2 pr-4">{{ t('admin.created') }}</th>
            <th class="py-2 pr-4">{{ t('admin.status') }}</th>
            <th class="py-2"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id" class="border-t border-zinc-100">
            <td class="py-2 pr-4">
              <div>{{ u.email }}</div>
              <div class="text-xs text-zinc-400">{{ u.full_name ?? '—' }}</div>
            </td>
            <td class="py-2 pr-4">
              <span class="inline-block px-2 py-0.5 text-xs rounded-full bg-zinc-100 text-zinc-700">
                {{ u.role }}
              </span>
            </td>
            <td class="py-2 pr-4 text-zinc-500 whitespace-nowrap">{{ new Date(u.created_at).toLocaleDateString() }}</td>
            <td class="py-2 pr-4">
              <span v-if="u.active" class="inline-flex items-center gap-1 text-success-600">
                <CheckCircle2 class="w-4 h-4" /> {{ t('admin.active') }}
              </span>
              <span v-else class="inline-flex items-center gap-1 text-danger-600">
                <XCircle class="w-4 h-4" /> {{ t('admin.inactive') }}
              </span>
            </td>
            <td class="py-2 text-right">
              <button
                class="btn-secondary"
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
      <p v-if="!loading && !users.length" class="text-sm text-zinc-500 py-4 text-center">
        {{ t('admin.noUsers') }}
      </p>
    </div>
  </div>
</template>
