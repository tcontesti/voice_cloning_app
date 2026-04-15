<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { LogIn } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'
import { ApiError } from '@/api/client'
import LED from '@/ui/primitives/LED.vue'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const error = ref<string | null>(null)

async function submit() {
  error.value = null
  try {
    await auth.login(email.value, password.value)
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch (e) {
    error.value =
      e instanceof ApiError && e.status === 401
        ? t('auth.errors.invalid')
        : t('auth.errors.network')
  }
}
</script>

<template>
  <form class="login studio-card" @submit.prevent="submit" novalidate>
    <header class="login__head">
      <div class="login__brand">
        <LED color="accent" on size="sm" />
        <span class="studio-label">VOICE CLONING · CLINICAL</span>
      </div>
      <h2 class="display-2 login__title">{{ t('auth.loginTitle') }}</h2>
      <p class="login__hint">Acceso restringido a personal autorizado.</p>
    </header>

    <div class="login__field" :class="{ 'login__field--filled': email }">
      <input id="email" v-model="email" type="email" autocomplete="username"
             required class="login__input" placeholder=" " />
      <label for="email" class="login__label">{{ t('auth.email') }}</label>
    </div>

    <div class="login__field" :class="{ 'login__field--filled': password }">
      <input id="password" v-model="password" type="password"
             autocomplete="current-password" required class="login__input" placeholder=" " />
      <label for="password" class="login__label">{{ t('auth.password') }}</label>
    </div>

    <p v-if="error" class="login__error" role="alert">{{ error }}</p>

    <button type="submit" class="btn btn-primary login__submit" :disabled="auth.loading">
      <LogIn class="w-4 h-4" />
      {{ auth.loading ? t('common.loading') : t('auth.submit') }}
    </button>

    <footer class="login__foot studio-value">
      {{ t('app.hospital') }}
    </footer>
  </form>
</template>

<style scoped>
.login {
  width: 420px;
  max-width: 100%;
  padding: 32px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.login__head { display: flex; flex-direction: column; gap: 6px; }
.login__brand { display: flex; align-items: center; gap: 10px; color: var(--fg-1); }
.login__title { margin: 4px 0 0; color: var(--fg-0); letter-spacing: -0.02em; }
.login__hint { margin: 0; color: var(--fg-2); font-size: 13px; }

.login__field { position: relative; }
.login__input {
  width: 100%;
  padding: 22px 14px 10px;
  background: var(--bg-2);
  border: 1px solid var(--line);
  border-radius: var(--radius-4);
  color: var(--fg-0);
  font-size: 15px;
  font-family: var(--font-sans);
  transition: border-color var(--dur-base) var(--ease-studio),
              box-shadow var(--dur-base) var(--ease-studio);
}
.login__input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 20%, transparent);
}
.login__label {
  position: absolute;
  left: 14px;
  top: 15px;
  font-family: var(--font-mono);
  font-size: 13px;
  letter-spacing: 0.04em;
  color: var(--fg-2);
  pointer-events: none;
  transition: transform var(--dur-base) var(--ease-studio),
              color var(--dur-base) var(--ease-studio),
              font-size var(--dur-base) var(--ease-studio);
}
.login__field--filled .login__label,
.login__field:focus-within .login__label {
  transform: translateY(-10px);
  font-size: 10px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--accent-glow);
}

.login__submit {
  padding: 14px;
  font-family: var(--font-mono);
  font-size: 13px;
  letter-spacing: 0.12em;
  margin-top: 4px;
}
.login__error {
  margin: 0;
  padding: 10px 14px;
  background: color-mix(in srgb, var(--signal-red) 12%, var(--bg-1));
  border: 1px solid var(--signal-red);
  border-radius: var(--radius-3);
  color: var(--signal-red);
  font-family: var(--font-mono);
  font-size: 12px;
}
.login__foot {
  margin-top: 6px;
  text-align: center;
  color: var(--fg-2);
}
</style>
