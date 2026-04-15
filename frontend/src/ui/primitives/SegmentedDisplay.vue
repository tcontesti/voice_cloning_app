<!--
  SegmentedDisplay — LCD-style label. Not a real 7-segment — that would be
  overkill and hard to read. Instead: monospaced text on a dim green/amber
  phosphor panel with scanlines, matching the "old hardware" vibe.
-->
<script setup lang="ts">
withDefaults(
  defineProps<{
    text: string
    tint?: 'green' | 'amber' | 'red' | 'blue'
    size?: 'sm' | 'md' | 'lg'
    blink?: boolean
    label?: string
  }>(),
  { tint: 'green', size: 'md' },
)
</script>

<template>
  <div class="seg" :class="[`seg--${tint}`, `seg--${size}`]" :aria-label="label ?? text">
    <span v-if="label" class="seg__label studio-label">{{ label }}</span>
    <div class="seg__panel">
      <span class="seg__ghost" aria-hidden="true">{{ text.replace(/./g, '8') }}</span>
      <span class="seg__text" :class="{ 'seg__text--blink': blink }">{{ text }}</span>
    </div>
  </div>
</template>

<style scoped>
.seg {
  display: inline-flex;
  flex-direction: column;
  gap: 4px;
  --seg-color: var(--signal-green);
}
.seg--green { --seg-color: #3dffb3; }
.seg--amber { --seg-color: #ffbe4a; }
.seg--red   { --seg-color: #ff3b5c; }
.seg--blue  { --seg-color: #6ed0ff; }

.seg__panel {
  position: relative;
  background:
    linear-gradient(180deg, #080d0a 0%, #10181a 100%);
  border: 1px solid var(--line);
  border-radius: var(--radius-3);
  padding: 6px 10px;
  box-shadow:
    inset 0 1px 2px rgba(0, 0, 0, 0.8),
    inset 0 0 8px rgba(0, 0, 0, 0.4);
  overflow: hidden;
  line-height: 1.1;
}
/* Scanlines */
.seg__panel::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    repeating-linear-gradient(
      to bottom,
      rgba(255, 255, 255, 0.0) 0 2px,
      rgba(0, 0, 0, 0.18) 2px 3px
    );
  pointer-events: none;
}

.seg__ghost,
.seg__text {
  display: block;
  font-family: var(--font-mono);
  font-weight: 500;
  letter-spacing: 0.06em;
  font-variant-numeric: tabular-nums;
  white-space: pre;
}
.seg__ghost {
  position: absolute;
  top: 6px;
  left: 10px;
  color: var(--seg-color);
  opacity: 0.08;
}
.seg__text {
  position: relative;
  color: var(--seg-color);
  text-shadow:
    0 0 4px color-mix(in srgb, var(--seg-color) 70%, transparent),
    0 0 12px color-mix(in srgb, var(--seg-color) 40%, transparent);
}
.seg__text--blink {
  animation: segBlink 1s steps(2, end) infinite;
}
@keyframes segBlink {
  0%, 60% { opacity: 1; }
  60.01%, 100% { opacity: 0.25; }
}

.seg--sm .seg__ghost,
.seg--sm .seg__text { font-size: 12px; }
.seg--md .seg__ghost,
.seg--md .seg__text { font-size: 16px; }
.seg--lg .seg__ghost,
.seg--lg .seg__text { font-size: 22px; }

.seg__label { color: var(--fg-2); }
</style>
