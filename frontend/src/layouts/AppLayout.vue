<script setup lang="ts">
import { RouterLink, RouterView, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { LogOut, Mic, Home, Wand2, Users, FileSearch, History, AudioWaveform } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import LED from '@/ui/primitives/LED.vue'

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
  <div class="shell">
    <header class="shell__top">
      <div class="shell__top-inner">
        <div class="shell__brand">
          <LED color="accent" on size="sm" />
          <RouterLink :to="{ name: 'home' }" class="shell__brand-title">
            {{ t('app.title') }}
          </RouterLink>
        </div>
        <nav class="shell__nav">
          <RouterLink :to="{ name: 'home' }" class="shell__link">
            <Home class="w-4 h-4" /><span>{{ t('nav.home') }}</span>
          </RouterLink>
          <RouterLink :to="{ name: 'record' }" class="shell__link">
            <Mic class="w-4 h-4" /><span>{{ t('nav.record') }}</span>
          </RouterLink>
          <RouterLink :to="{ name: 'profiles' }" class="shell__link">
            <AudioWaveform class="w-4 h-4" /><span>{{ t('nav.profiles') ?? 'Perfiles' }}</span>
          </RouterLink>
          <RouterLink :to="{ name: 'synthesize' }" class="shell__link">
            <Wand2 class="w-4 h-4" /><span>{{ t('nav.synthesize') }}</span>
          </RouterLink>
          <RouterLink :to="{ name: 'history' }" class="shell__link">
            <History class="w-4 h-4" /><span>{{ t('nav.history') }}</span>
          </RouterLink>
          <RouterLink v-if="isAdmin" :to="{ name: 'admin-users' }" class="shell__link">
            <Users class="w-4 h-4" /><span>{{ t('nav.admin') }}</span>
          </RouterLink>
          <RouterLink v-if="canAudit" :to="{ name: 'audit' }" class="shell__link">
            <FileSearch class="w-4 h-4" /><span>{{ t('nav.audit') }}</span>
          </RouterLink>
        </nav>
        <div class="shell__user">
          <span class="shell__user-email">{{ auth.user?.email }}</span>
          <button class="shell__logout" @click="logout" :aria-label="t('nav.logout')">
            <LogOut class="w-4 h-4" /><span>{{ t('nav.logout') }}</span>
          </button>
        </div>
      </div>
    </header>

    <main class="shell__main">
      <RouterView />
    </main>

    <footer class="shell__foot">
      <span class="studio-value">{{ t('app.hospital') }}</span>
      <span class="studio-value shell__foot-sep">·</span>
      <span class="studio-value">UI · studio · v2</span>
    </footer>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  display: grid;
  grid-template-rows: 56px 1fr 28px;
  background: var(--bg-0);
  color: var(--fg-0);
}

.shell__top {
  background: var(--bg-1);
  border-bottom: 1px solid var(--line);
}
.shell__top-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 0 24px;
  height: 56px;
  display: flex;
  align-items: center;
  gap: 24px;
}
.shell__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-right: 16px;
  border-right: 1px solid var(--line);
  margin-right: 8px;
}
.shell__brand-title {
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 14px;
  letter-spacing: -0.01em;
  color: var(--fg-0);
  text-decoration: none;
}
.shell__nav {
  display: flex;
  align-items: center;
  gap: 2px;
}
.shell__link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-3);
  color: var(--fg-1);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-decoration: none;
  transition: color var(--dur-base) var(--ease-studio),
              background var(--dur-base) var(--ease-studio);
}
.shell__link:hover { color: var(--fg-0); background: var(--bg-2); }
.shell__link.router-link-active {
  color: var(--accent-glow);
  background: color-mix(in srgb, var(--accent) 14%, transparent);
}
.shell__link span { white-space: nowrap; }

.shell__user { margin-left: auto; display: flex; align-items: center; gap: 10px; }
.shell__user-email {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--fg-2);
  letter-spacing: 0.02em;
}
.shell__logout {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-radius: var(--radius-3);
  color: var(--fg-1);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: border-color var(--dur-base) var(--ease-studio),
              color var(--dur-base) var(--ease-studio);
}
.shell__logout:hover { border-color: var(--line-2); color: var(--fg-0); }

.shell__main {
  padding: 28px 24px;
  max-width: 1440px;
  margin: 0 auto;
  width: 100%;
}

.shell__foot {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: var(--bg-1);
  border-top: 1px solid var(--line);
  color: var(--fg-2);
}
.shell__foot-sep { opacity: 0.5; }

@media (max-width: 900px) {
  .shell__nav { display: none; }
}
</style>
