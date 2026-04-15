<!--
  ModelCard — selectable card for a TTS model. All clickable; parent owns
  selection. Badges reflect cloud / local / clinical-safe. Mini metrics
  are passed in from the parent (not sourced here).
-->
<script setup lang="ts">
import { computed } from 'vue'
import LED from '@/ui/primitives/LED.vue'

interface Metric { label: string; value: string }

const props = withDefaults(
  defineProps<{
    name: string
    license: string
    notes?: string
    selected?: boolean
    available?: boolean
    loading?: boolean
    cloud?: boolean
    clinicalSafe?: boolean
    metrics?: Metric[]
  }>(),
  { available: true, clinicalSafe: true, metrics: () => [] },
)

const emit = defineEmits<{ (e: 'select'): void }>()

const statusColor = computed<'green' | 'amber' | 'red' | 'off' | 'accent'>(() => {
  if (!props.available) return 'off'
  if (props.loading) return 'amber'
  if (props.selected) return 'accent'
  return 'green'
})
</script>

<template>
  <button
    type="button"
    class="mcard studio-card"
    :class="{ 'mcard--selected': selected, 'mcard--disabled': !available }"
    :aria-pressed="selected"
    :disabled="!available"
    @click="emit('select')"
  >
    <header class="mcard__head">
      <div class="mcard__badges">
        <span v-if="cloud" class="mcard__badge mcard__badge--cloud">CLOUD</span>
        <span v-else class="mcard__badge mcard__badge--local">LOCAL</span>
        <span v-if="clinicalSafe" class="mcard__badge mcard__badge--safe">CLINICAL · SAFE</span>
        <span v-else class="mcard__badge mcard__badge--unsafe">NO CLÍNICO</span>
      </div>
      <LED :color="statusColor" :pulse="loading" size="sm" />
    </header>

    <div class="mcard__title display-2">{{ name.toUpperCase() }}</div>
    <div class="mcard__license studio-value">{{ license }}</div>
    <p v-if="notes" class="mcard__notes">{{ notes }}</p>

    <ul v-if="metrics.length" class="mcard__metrics">
      <li v-for="m in metrics" :key="m.label">
        <span class="studio-label">{{ m.label }}</span>
        <span class="studio-value mcard__metric-val">{{ m.value }}</span>
      </li>
    </ul>
  </button>
</template>

<style scoped>
.mcard {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 20px;
  text-align: left;
  cursor: pointer;
  background: var(--bg-1);
  border: 1px solid var(--line);
  transition: transform var(--dur-base) var(--ease-studio),
              border-color var(--dur-base) var(--ease-studio),
              box-shadow var(--dur-base) var(--ease-studio);
}
.mcard:hover:not(:disabled) { transform: translateY(-1px); border-color: var(--line-2); }
.mcard--selected {
  border-color: var(--accent);
  box-shadow:
    var(--shadow-card),
    0 0 0 1px var(--accent),
    0 0 24px color-mix(in srgb, var(--accent) 30%, transparent);
}
.mcard--disabled { opacity: 0.5; cursor: not-allowed; }

.mcard__head { display: flex; align-items: center; justify-content: space-between; }
.mcard__badges { display: flex; gap: 6px; flex-wrap: wrap; }
.mcard__badge {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.1em;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid var(--line);
  color: var(--fg-1);
}
.mcard__badge--cloud { color: var(--signal-blue); border-color: color-mix(in srgb, var(--signal-blue) 40%, transparent); }
.mcard__badge--local { color: var(--signal-green); border-color: color-mix(in srgb, var(--signal-green) 40%, transparent); }
.mcard__badge--safe  { color: var(--fg-0); }
.mcard__badge--unsafe { color: var(--signal-red); border-color: color-mix(in srgb, var(--signal-red) 40%, transparent); }

.mcard__title { margin: 4px 0; letter-spacing: -0.015em; }
.mcard__license { color: var(--fg-2); }
.mcard__notes { color: var(--fg-1); font-size: 13px; line-height: 1.5; margin: 0; }

.mcard__metrics {
  list-style: none;
  margin: 8px 0 0;
  padding: 12px 0 0;
  border-top: 1px solid var(--line);
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.mcard__metrics li { display: flex; flex-direction: column; gap: 2px; }
.mcard__metric-val { font-size: 16px; color: var(--fg-0); font-family: var(--font-mono); font-weight: 500; }
</style>
