<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <div class="public">
    <div class="public__bg" aria-hidden="true" />
    <div class="public__shell">
      <RouterView />
    </div>
  </div>
</template>

<style scoped>
.public {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: var(--bg-0);
  overflow: hidden;
  padding: 48px 16px;
}
.public__bg {
  position: absolute;
  inset: -20%;
  background:
    radial-gradient(600px 400px at 30% 30%, color-mix(in srgb, var(--accent) 18%, transparent), transparent 60%),
    radial-gradient(500px 500px at 70% 70%, color-mix(in srgb, var(--signal-blue) 10%, transparent), transparent 60%);
  filter: blur(30px);
  animation: drift 28s ease-in-out infinite alternate;
  z-index: 0;
}
.public__shell { position: relative; z-index: 1; width: 100%; max-width: 480px; }

@keyframes drift {
  0%   { transform: translate(0, 0) scale(1); }
  50%  { transform: translate(2%, -3%) scale(1.05); }
  100% { transform: translate(-3%, 2%) scale(0.98); }
}
@media (prefers-reduced-motion: reduce) {
  .public__bg { animation: none; }
}
</style>
