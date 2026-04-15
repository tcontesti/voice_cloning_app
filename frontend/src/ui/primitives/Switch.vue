<!--
  Switch — physical-looking toggle. Click / Space / Enter to flip. Slightly
  dampened animation to convey mechanical "resistance" of a hardware toggle.
-->
<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    modelValue: boolean
    label?: string
    disabled?: boolean
    size?: 'sm' | 'md'
  }>(),
  { size: 'md' },
)

const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()

function toggle(e: Event) {
  if (props.disabled) return
  e.preventDefault()
  emit('update:modelValue', !props.modelValue)
}

function onKey(e: KeyboardEvent) {
  if (props.disabled) return
  if (e.key === ' ' || e.key === 'Enter') toggle(e)
}
</script>

<template>
  <label class="studio-switch" :class="[`studio-switch--${size}`, { 'studio-switch--on': modelValue, 'studio-switch--disabled': disabled }]">
    <span
      class="studio-switch__body studio-focus"
      role="switch"
      :aria-checked="modelValue"
      :aria-disabled="disabled"
      :aria-label="label ?? undefined"
      :tabindex="disabled ? -1 : 0"
      @click="toggle"
      @keydown="onKey"
    >
      <span class="studio-switch__cap" />
    </span>
    <span v-if="label" class="studio-switch__label studio-label">{{ label }}</span>
  </label>
</template>

<style scoped>
.studio-switch {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  user-select: none;
}
.studio-switch__body {
  position: relative;
  display: inline-block;
  background: var(--bg-0);
  border: 1px solid var(--line);
  border-radius: 999px;
  box-shadow:
    inset 0 2px 4px rgba(0, 0, 0, 0.6),
    inset 0 -1px 0 rgba(255, 255, 255, 0.03);
  transition: background var(--dur-base) var(--ease-studio),
              border-color var(--dur-base) var(--ease-studio);
  cursor: pointer;
}
.studio-switch--sm .studio-switch__body { width: 36px; height: 20px; }
.studio-switch--md .studio-switch__body { width: 48px; height: 26px; }

.studio-switch__cap {
  position: absolute;
  top: 2px;
  left: 2px;
  background: linear-gradient(180deg, #2e2e36 0%, #16161b 100%);
  border: 1px solid var(--line-2);
  border-radius: 999px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.06),
    0 2px 4px rgba(0, 0, 0, 0.7);
  transition: transform var(--dur-slow) cubic-bezier(0.5, 1.8, 0.3, 1),
              background var(--dur-base) var(--ease-studio);
}
.studio-switch--sm .studio-switch__cap { width: 14px; height: 14px; }
.studio-switch--md .studio-switch__cap { width: 20px; height: 20px; }

.studio-switch--on .studio-switch__body {
  background: color-mix(in srgb, var(--accent) 28%, var(--bg-0));
  border-color: var(--accent);
  box-shadow:
    inset 0 2px 4px rgba(0, 0, 0, 0.4),
    0 0 0 1px color-mix(in srgb, var(--accent) 40%, transparent),
    0 0 12px color-mix(in srgb, var(--accent) 25%, transparent);
}
.studio-switch--on.studio-switch--sm .studio-switch__cap { transform: translateX(16px); }
.studio-switch--on.studio-switch--md .studio-switch__cap { transform: translateX(22px); }

.studio-switch--disabled { opacity: 0.5; }
.studio-switch--disabled .studio-switch__body { cursor: not-allowed; }

.studio-switch__label { cursor: pointer; }
.studio-switch--disabled .studio-switch__label { cursor: not-allowed; }
</style>
