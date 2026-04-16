<script setup lang="ts">
import { RouterView } from 'vue-router'

// Auth bootstrap runs in main.ts before app.mount() so the first navigation
// guard already sees the rehydrated token. Don't re-call it here — a second
// bootstrap fires a redundant /auth/me and briefly flips the UI to loading.
</script>

<template>
  <RouterView />
</template>
