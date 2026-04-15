<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import RecorderStudio from '@/ui/composites/RecorderStudio.vue'
import type { Profile } from '@/api/synthesis'

const { t } = useI18n()
const lastProfile = ref<Profile | null>(null)

function onProfileCreated(p: Profile) {
  lastProfile.value = p
}
</script>

<template>
  <div class="record-view">
    <RecorderStudio @profile-created="onProfileCreated" />

    <div v-if="lastProfile" class="record-view__confirm studio-card" role="status">
      <div class="studio-label">PROFILE CREADO</div>
      <div class="record-view__confirm-name">{{ lastProfile.name }}</div>
      <div class="studio-value">
        {{ lastProfile.reference_ids.length }} ref · {{ t('common.id') ?? 'id' }} {{ lastProfile.id.slice(0, 8) }}
      </div>
      <RouterLink :to="{ name: 'synthesize' }" class="btn btn-primary record-view__cta">
        {{ t('nav.synthesize') }} →
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.record-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.record-view__confirm {
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
  padding: 20px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 18px;
  align-items: center;
  border-color: var(--accent);
}
.record-view__confirm-name {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 20px;
  color: var(--fg-0);
  letter-spacing: -0.01em;
}
.record-view__cta {
  padding: 10px 18px;
  font-family: var(--font-mono);
  font-size: 12px;
  letter-spacing: 0.1em;
}
</style>
