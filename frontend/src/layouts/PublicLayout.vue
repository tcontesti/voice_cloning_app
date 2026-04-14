<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
</script>

<template>
  <div class="min-h-full grid place-items-center px-4 py-12 bg-zinc-50">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <div class="text-xs uppercase tracking-widest text-zinc-500">{{ t('app.hospital') }}</div>
        <h1 class="mt-2 text-2xl font-semibold text-accent-700">{{ t('app.title') }}</h1>
      </div>
      <RouterView />
    </div>
  </div>
</template>
