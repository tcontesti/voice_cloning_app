<!--
  Knob — rotary control. Drag vertical = value change; Shift+drag = fine;
  double-click = reset to default. Keyboard: arrows step, PgUp/Dn step*10.
  A11y: role=slider with aria-valuenow / aria-valuetext. Focus ring via
  .studio-focus utility.

  Arc rendered with two SVG paths (trail + fill) plus a triangular indicator
  rotated around the knob centre. 270° sweep (from -135° to +135°).
-->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type KnobSize = 32 | 48 | 64

const props = withDefaults(
  defineProps<{
    modelValue: number
    min?: number
    max?: number
    step?: number
    default?: number
    label?: string
    unit?: string
    size?: KnobSize
    disabled?: boolean
    precision?: number
  }>(),
  {
    min: 0,
    max: 1,
    step: 0.01,
    default: 0,
    size: 48,
    disabled: false,
    precision: 2,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', v: number): void
}>()

const SWEEP_DEG = 270 // full travel
const START_DEG = -135 // 7-o'clock position

const normalised = computed(() => {
  const span = props.max - props.min
  if (span <= 0) return 0
  return Math.max(0, Math.min(1, (props.modelValue - props.min) / span))
})

const angle = computed(() => START_DEG + normalised.value * SWEEP_DEG)

const displayValue = computed(() => {
  const v = props.modelValue
  const p = props.precision
  return Number.isFinite(v) ? v.toFixed(p) : '—'
})

// --- drag handling ---------------------------------------------------------
const dragging = ref(false)
let startY = 0
let startValue = 0
let shiftMode = false

function clamp(v: number) {
  return Math.max(props.min, Math.min(props.max, v))
}

function snap(v: number) {
  const step = props.step
  if (!step) return v
  const snapped = Math.round((v - props.min) / step) * step + props.min
  return Number(snapped.toFixed(6))
}

function onPointerDown(e: PointerEvent) {
  if (props.disabled) return
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
  dragging.value = true
  startY = e.clientY
  startValue = props.modelValue
  shiftMode = e.shiftKey
  e.preventDefault()
}

function onPointerMove(e: PointerEvent) {
  if (!dragging.value) return
  const dy = startY - e.clientY // up = positive
  // Full travel in 200px; shift = fine (5× slower).
  const pxPerFullRange = shiftMode ? 1000 : 200
  const delta = (dy / pxPerFullRange) * (props.max - props.min)
  const next = snap(clamp(startValue + delta))
  if (next !== props.modelValue) emit('update:modelValue', next)
}

function onPointerUp(e: PointerEvent) {
  if (!dragging.value) return
  dragging.value = false
  try { (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId) } catch { /* noop */ }
}

function onDoubleClick() {
  if (props.disabled) return
  emit('update:modelValue', clamp(props.default))
}

function onWheel(e: WheelEvent) {
  if (props.disabled) return
  e.preventDefault()
  const dir = e.deltaY < 0 ? 1 : -1
  const mult = e.shiftKey ? 0.2 : 1
  const next = snap(clamp(props.modelValue + dir * props.step * mult * 5))
  if (next !== props.modelValue) emit('update:modelValue', next)
}

// --- keyboard --------------------------------------------------------------
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
    case 'PageUp':
      delta = props.step * 10; break
    case 'PageDown':
      delta = -props.step * 10; break
    case 'Home':
      emit('update:modelValue', props.min); e.preventDefault(); return
    case 'End':
      emit('update:modelValue', props.max); e.preventDefault(); return
    default: return
  }
  e.preventDefault()
  emit('update:modelValue', snap(clamp(props.modelValue + delta)))
}

// Arc path geometry: draw from startDeg to startDeg + sweep.
function describeArc(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
  const toRad = (d: number) => (d - 90) * Math.PI / 180
  const s = { x: cx + r * Math.cos(toRad(startDeg)), y: cy + r * Math.sin(toRad(startDeg)) }
  const e = { x: cx + r * Math.cos(toRad(endDeg)), y: cy + r * Math.sin(toRad(endDeg)) }
  const large = endDeg - startDeg > 180 ? 1 : 0
  return `M ${s.x.toFixed(3)} ${s.y.toFixed(3)} A ${r} ${r} 0 ${large} 1 ${e.x.toFixed(3)} ${e.y.toFixed(3)}`
}

const viewBox = computed(() => {
  const s = props.size
  return `0 0 ${s} ${s}`
})
const arcRadius = computed(() => props.size / 2 - 6)
const center = computed(() => props.size / 2)
const trailPath = computed(() =>
  describeArc(center.value, center.value, arcRadius.value, START_DEG, START_DEG + SWEEP_DEG),
)
const fillPath = computed(() =>
  describeArc(center.value, center.value, arcRadius.value, START_DEG, angle.value),
)
const strokeWidth = computed(() => (props.size === 32 ? 3 : props.size === 48 ? 4 : 5))

watch(dragging, (v) => {
  // Hover/drag visual state is handled via CSS; ref only used for focus styling.
  void v
})

const ariaValueText = computed(() => {
  const unit = props.unit ? ` ${props.unit}` : ''
  return `${displayValue.value}${unit}`
})
</script>

<template>
  <div
    class="studio-knob"
    :class="{ 'studio-knob--dragging': dragging, 'studio-knob--disabled': disabled }"
    :style="{ width: size + 'px' }"
  >
    <div v-if="label" class="studio-label studio-knob__label">{{ label }}</div>

    <div
      class="studio-knob__body studio-focus"
      role="slider"
      :tabindex="disabled ? -1 : 0"
      :aria-valuemin="min"
      :aria-valuemax="max"
      :aria-valuenow="modelValue"
      :aria-valuetext="ariaValueText"
      :aria-label="label ?? 'knob'"
      :aria-disabled="disabled"
      :style="{ width: size + 'px', height: size + 'px' }"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerUp"
      @dblclick="onDoubleClick"
      @wheel.passive="onWheel"
      @keydown="onKeyDown"
    >
      <svg :viewBox="viewBox" :width="size" :height="size" aria-hidden="true">
        <!-- Trail -->
        <path
          :d="trailPath"
          fill="none"
          stroke="var(--line)"
          :stroke-width="strokeWidth"
          stroke-linecap="round"
        />
        <!-- Fill -->
        <path
          :d="fillPath"
          fill="none"
          stroke="var(--accent)"
          :stroke-width="strokeWidth"
          stroke-linecap="round"
          filter="url(#knob-glow)"
        />
        <defs>
          <filter id="knob-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="1.2" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
      </svg>

      <!-- Physical cap with triangular indicator -->
      <div
        class="studio-knob__cap"
        :style="{
          transform: `rotate(${angle}deg)`,
          width: (size - 14) + 'px',
          height: (size - 14) + 'px',
        }"
      >
        <div class="studio-knob__tick" />
      </div>
    </div>

    <div class="studio-knob__value studio-value">
      {{ displayValue }}<span v-if="unit" class="studio-knob__unit">{{ unit }}</span>
    </div>
  </div>
</template>

<style scoped>
.studio-knob {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  user-select: none;
}
.studio-knob__label {
  margin-bottom: 2px;
}
.studio-knob__body {
  position: relative;
  background: var(--bg-2);
  border-radius: 50%;
  border: 1px solid var(--line);
  box-shadow:
    inset 0 2px 4px rgba(0, 0, 0, 0.5),
    inset 0 -1px 0 rgba(255, 255, 255, 0.03);
  cursor: grab;
  transition: box-shadow var(--dur-base) var(--ease-studio);
}
.studio-knob__body:hover,
.studio-knob--dragging .studio-knob__body {
  box-shadow:
    inset 0 2px 4px rgba(0, 0, 0, 0.5),
    inset 0 -1px 0 rgba(255, 255, 255, 0.03),
    var(--shadow-knob-hover);
}
.studio-knob--dragging .studio-knob__body { cursor: grabbing; }
.studio-knob--disabled .studio-knob__body {
  cursor: not-allowed;
  opacity: 0.4;
}

.studio-knob__body svg {
  display: block;
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.studio-knob__cap {
  position: absolute;
  top: 50%;
  left: 50%;
  translate: -50% -50%;
  border-radius: 50%;
  background:
    radial-gradient(circle at 30% 30%, #2c2c34 0%, #16161b 60%, #0d0d11 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.05),
    0 2px 3px rgba(0, 0, 0, 0.6);
  transition: transform var(--dur-base) var(--ease-studio);
}
.studio-knob--dragging .studio-knob__cap { transition: none; }

.studio-knob__tick {
  position: absolute;
  top: 6%;
  left: 50%;
  width: 2px;
  height: 22%;
  border-radius: 2px;
  background: var(--fg-0);
  transform: translateX(-50%);
  box-shadow: 0 0 4px var(--accent-glow);
}

.studio-knob__value {
  margin-top: 2px;
  font-variant-numeric: tabular-nums;
}
.studio-knob__unit {
  margin-left: 2px;
  color: var(--fg-2);
}
</style>
