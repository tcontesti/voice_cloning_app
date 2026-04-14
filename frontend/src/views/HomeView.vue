<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Mic, FileSignature } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-semibold">{{ t('app.title') }}</h1>
    <p class="text-zinc-600">
      Bienvenido/a, {{ auth.user?.full_name ?? auth.user?.email }}.
    </p>

    <div class="grid sm:grid-cols-2 gap-4">
      <RouterLink :to="{ name: 'consent' }" class="card hover:ring-accent-300 transition">
        <FileSignature class="w-6 h-6 text-accent-600 mb-2" />
        <h3 class="font-medium">{{ t('consent.title') }}</h3>
        <p class="text-sm text-zinc-600 mt-1">Antes de grabar, debe leer y firmar el consentimiento.</p>
      </RouterLink>

      <RouterLink :to="{ name: 'record' }" class="card hover:ring-accent-300 transition">
        <Mic class="w-6 h-6 text-accent-600 mb-2" />
        <h3 class="font-medium">{{ t('nav.record') }}</h3>
        <p class="text-sm text-zinc-600 mt-1">Grabe muestras de su voz para crear su perfil vocal.</p>
      </RouterLink>
    </div>
  </div>
</template>
