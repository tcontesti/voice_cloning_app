<!--
  LED — small glowing dot. Pure CSS, no deps.
  Colour resolved via CSS custom property so the parent controls the palette.
-->
<script setup lang="ts">
import { computed } from 'vue'

type LedColor = 'green' | 'amber' | 'red' | 'blue' | 'accent' | 'off'
type LedSize = 'xs' | 'sm' | 'md'

const props = withDefaults(
  defineProps<{
    color?: LedColor
    size?: LedSize
    on?: boolean
    pulse?: boolean
    label?: string
  }>(),
  { color: 'green', size: 'sm', on: true, pulse: false },
)

const paletteVar = computed(() => {
  if (!props.on || props.color === 'off') return 'var(--meter-off)'
  switch (props.color) {
    case 'green': return 'var(--signal-green)'
    case 'amber': return 'var(--signal-amber)'
    case 'red':   return 'var(--signal-red)'
    case 'blue':  return 'var(--signal-blue)'
    case 'accent': return 'var(--accent-glow)'
    default: return 'var(--meter-off)'
  }
})

const dim = computed(() => (props.size === 'xs' ? 6 : props.size === 'md' ? 12 : 8))
</script>

<template>
  <span class="studio-led" :aria-label="label ?? undefined" role="status">
    <span
      class="studio-led__dot"
      :class="{ 'studio-led__dot--on': on, 'studio-led__dot--pulse': on && pulse }"
      :style="{
        '--led-color': paletteVar,
        '--led-size': dim + 'px',
      }"
    />
    <span v-if="label" class="studio-led__label">{{ label }}</span>
  </span>
</template>

<style scoped>
.studio-led {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.studio-led__dot {
  width: var(--led-size);
  height: var(--led-size);
  border-radius: 999px;
  background: var(--led-color);
  color: var(--led-color);
  /* Ring that simulates a recessed PCB hole — visible even when off. */
  box-shadow:
    inset 0 0 0 1px rgba(0, 0, 0, 0.7),
    inset 0 1px 2px rgba(0, 0, 0, 0.4);
  transition: background var(--dur-fast) var(--ease-studio);
}
.studio-led__dot--on {
  /* Realismo: encendido instantáneo (0ms), apagado 40ms (ver tokens.css). */
  transition: background 0ms, box-shadow var(--dur-fast) var(--ease-studio);
  box-shadow:
    inset 0 0 0 1px rgba(0, 0, 0, 0.7),
    0 0 6px currentColor,
    0 0 12px color-mix(in srgb, currentColor 40%, transparent);
}
.studio-led__dot--pulse {
  animation: ledPulse 1.2s var(--ease-studio) infinite;
}
@keyframes ledPulse {
  0%, 100% { filter: brightness(1); }
  50% { filter: brightness(1.5); }
}
.studio-led__label {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--fg-1);
}
</style>
