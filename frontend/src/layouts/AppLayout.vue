<script setup lang="ts">
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { LogOut, Mic, Home, Wand2, Users, FileSearch } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()

const isAdmin = computed(() => auth.role === 'admin')
const canAudit = computed(() => auth.role === 'admin' || auth.role === 'auditor')

function logout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="min-h-full flex flex-col">
    <header class="border-b border-zinc-200 bg-white">
      <div class="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <div class="flex items-center gap-8">
          <RouterLink :to="{ name: 'home' }" class="font-semibold text-accent-700">
            {{ t('app.title') }}
          </RouterLink>
          <nav class="flex items-center gap-1 text-sm">
            <RouterLink :to="{ name: 'home' }" class="px-3 py-1.5 rounded-lg hover:bg-zinc-100 inline-flex items-center gap-2">
              <Home class="w-4 h-4" /> {{ t('nav.home') }}
            </RouterLink>
            <RouterLink :to="{ name: 'record' }" class="px-3 py-1.5 rounded-lg hover:bg-zinc-100 inline-flex items-center gap-2">
              <Mic class="w-4 h-4" /> {{ t('nav.record') }}
            </RouterLink>
            <RouterLink :to="{ name: 'synthesize' }" class="px-3 py-1.5 rounded-lg hover:bg-zinc-100 inline-flex items-center gap-2">
              <Wand2 class="w-4 h-4" /> {{ t('nav.synthesize') }}
            </RouterLink>
            <RouterLink v-if="isAdmin" :to="{ name: 'admin-users' }" class="px-3 py-1.5 rounded-lg hover:bg-zinc-100 inline-flex items-center gap-2">
              <Users class="w-4 h-4" /> {{ t('nav.admin') }}
            </RouterLink>
            <RouterLink v-if="canAudit" :to="{ name: 'audit' }" class="px-3 py-1.5 rounded-lg hover:bg-zinc-100 inline-flex items-center gap-2">
              <FileSearch class="w-4 h-4" /> {{ t('nav.audit') }}
            </RouterLink>
          </nav>
        </div>
        <div class="flex items-center gap-3 text-sm">
          <span class="text-zinc-600">{{ auth.user?.email }}</span>
          <button class="btn-secondary" @click="logout">
            <LogOut class="w-4 h-4" /> {{ t('nav.logout') }}
          </button>
        </div>
      </div>
    </header>
    <main class="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
      <RouterView />
    </main>
  </div>
</template>
