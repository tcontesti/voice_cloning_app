import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router'
import { i18n } from './i18n'
import { useAuthStore } from './stores/auth'
import './ui/theme/index.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(i18n)

// Rehydrate auth from localStorage before mounting. If a token is present
// but /auth/me fails (expired/revoked), bootstrapFromStorage will auto-logout
// so the router guard redirects to /login on the first navigation.
void (async () => {
  await useAuthStore().bootstrapFromStorage()
  await router.isReady()
  app.mount('#app')
})()
