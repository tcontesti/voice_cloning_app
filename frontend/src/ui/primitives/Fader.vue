<!--
  Fader — vertical linear control. Drag cap = value. Keyboard & a11y match
  Knob: role=slider, arrows step, PgUp/Dn step*10, Home/End jump to min/max.
  Shift+drag = fine. Double-click = reset to default.

  Rail has graduations every 10% and a fill that grows from the bottom up
  following the cap. Cap is a rectangular LED with the accent glow.
-->
<script setup lang="ts">
import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: number
    min?: number
    max?: number
    step?: number
    default?: number
    label?: string
    unit?: string
    height?: 140 | 200
    disabled?: boolean
    precision?: number
  }>(),
  {
    min: 0,
    max: 1,
    step: 0.01,
    default: 0,
    height: 140,
    disabled: false,
    precision: 2,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: number): void
}>()

const railRef = ref<HTMLDivElement | null>(null)
const dragging = ref(false)
let shiftMode = false
let startY = 0
let startValue = 0

const normalised = computed(() => {
  const span = props.max - props.min
  if (span <= 0) return 0
  return Math.max(0, Math.min(1, (props.modelValue - props.min) / span))
})

// Tick positions at 10% increments.
const ticks = Array.from({ length: 11 }, (_, i) => i * 10)

const displayValue = computed(() => {
  const v = props.modelValue
  return Number.isFinite(v) ? v.toFixed(props.precision) : '—'
})

function clamp(v: number) { return Math.max(props.min, Math.min(props.max, v)) }
function snap(v: number) {
  const s = props.step
  if (!s) return v
  const snapped = Math.round((v - props.min) / s) * s + props.min
  return Number(snapped.toFixed(6))
}

function onPointerDown(e: PointerEvent) {
  if (props.disabled) return
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  dragging.value = true
  shiftMode = e.shiftKey
  startY = e.clientY
  startValue = props.modelValue
  e.preventDefault()
}

function onPointerMove(e: PointerEvent) {
  if (!dragging.value || !railRef.value) return
  const rect = railRef.value.getBoundingClientRect()
  const fullPx = shiftMode ? rect.height * 5 : rect.height
  const dy = startY - e.clientY
  const delta = (dy / fullPx) * (props.max - props.min)
  const next = snap(clamp(startValue + delta))
  if (next !== props.modelValue) emit('update:modelValue', next)
}

function onPointerUp(e: PointerEvent) {
  if (!dragging.value) return
  dragging.value = false
  try { (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId) } catch { /* noop */ }
}

function onTrackClick(e: PointerEvent) {
  if (props.disabled || dragging.value) return
  const rail = railRef.value
  if (!rail) return
  const rect = rail.getBoundingClientRect()
  const ratio = 1 - Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height))
  const next = snap(clamp(props.min + ratio * (props.max - props.min)))
  if (next !== props.modelValue) emit('update:modelValue', next)
}

function onDoubleClick() {
  if (props.disabled) return
  emit('update:modelValue', clamp(props.default))
}

function onKeyDown(e: KeyboardEvent) {
  if (props.disabled) return
  let delta = 0
  switch (e.key) {
    case 'ArrowUp':
    case 'ArrowRight':
      delta = props.step; break
    case 'ArrowDown':
    case 'ArrowLeft':
      delta = -props.step; break
    case 'PageUp':   delta = props.step * 10; break
    case 'PageDown': delta = -props.step * 10; break
    case 'Home': emit('update:modelValue', props.min); e.preventDefault(); return
    case 'End':  emit('update:modelValue', props.max); e.preventDefault(); return
    default: return
  }
  e.preventDefault()
  emit('update:modelValue', snap(clamp(props.modelValue + delta)))
}

const ariaValueText = computed(() =>
  props.unit ? `${displayValue.value} ${props.unit}` : displayValue.value,
)
</script>

<template>
  <div class="studio-fader" :class="{ 'studio-fader--disabled': disabled }">
    <div v-if="label" class="studio-label">{{ label }}</div>

    <div
      ref="railRef"
      class="studio-fader__rail"
      :style="{ height: height + 'px' }"
      @pointerdown="onTrackClick"
    >
      <div class="studio-fader__fill" :style="{ height: normalised * 100 + '%' }" />
      <div
        v-for="t in ticks"
        :key="t"
        class="studio-fader__tick"
        :class="{ 'studio-fader__tick--major': t % 50 === 0 }"
        :style="{ bottom: t + '%' }"
      />
      <div
        class="studio-fader__cap studio-focus"
        role="slider"
        :tabindex="disabled ? -1 : 0"
        :aria-valuemin="min"
        :aria-valuemax="max"
        :aria-valuenow="modelValue"
        :aria-valuetext="ariaValueText"
        :aria-label="label ?? 'fader'"
        :aria-disabled="disabled"
        :style="{ bottom: `calc(${normalised * 100}% - 9px)` }"
        @pointerdown.stop="onPointerDown"
        @pointermove.stop="onPointerMove"
        @pointerup.stop="onPointerUp"
        @pointercancel.stop="onPointerUp"
        @dblclick.stop="onDoubleClick"
        @keydown="onKeyDown"
      >
        <span class="studio-fader__cap-led" />
      </div>
    </div>

    <div class="studio-fader__value studio-value">
      {{ displayValue }}<span v-if="unit" class="studio-fader__unit">{{ unit }}</span>
    </div>
  </div>
</template>

<style scoped>
.studio-fader {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  user-select: none;
}

.studio-fader__rail {
  position: relative;
  width: 14px;
  background: var(--bg-0);
  border: 1px solid var(--line);
  border-radius: var(--radius-2);
  box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.6);
  cursor: pointer;
}

.studio-fader__fill {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    to top,
    color-mix(in srgb, var(--accent) 40%, transparent),
    color-mix(in srgb, var(--accent-glow) 60%, transparent)
  );
  box-shadow: 0 0 12px color-mix(in srgb, var(--accent) 40%, transparent);
  border-radius: var(--radius-2);
  transition: height var(--dur-base) var(--ease-studio);
}
.studio-fader:has(.studio-fader__cap:active) .studio-fader__fill { transition: none; }

.studio-fader__tick {
  position: absolute;
  left: -4px;
  right: -4px;
  height: 1px;
  background: var(--line-2);
  opacity: 0.35;
}
.studio-fader__tick--major {
  opacity: 0.7;
  background: var(--fg-2);
}

.studio-fader__cap {
  position: absolute;
  left: 50%;
  translate: -50% 0;
  width: 34px;
  height: 18px;
  background:
    linear-gradient(180deg, #2a2a32 0%, #15151a 100%);
  border: 1px solid var(--line-2);
  border-radius: var(--radius-2);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.05),
    0 2px 4px rgba(0, 0, 0, 0.6);
  cursor: grab;
  display: flex;
  align-items: center;
  justify-content: center;
}
.studio-fader__cap:active { cursor: grabbing; }

.studio-fader__cap-led {
  width: 22px;
  height: 3px;
  background: var(--accent-glow);
  border-radius: 2px;
  box-shadow:
    0 0 6px var(--accent-glow),
    0 0 12px color-mix(in srgb, var(--accent) 50%, transparent);
}

.studio-fader--disabled { opacity: 0.4; }
.studio-fader--disabled .studio-fader__cap { cursor: not-allowed; }

.studio-fader__value {
  font-variant-numeric: tabular-nums;
}
.studio-fader__unit { margin-left: 2px; color: var(--fg-2); }
</style>
