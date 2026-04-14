<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { ApiError } from '@/api/client'

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
  <form class="card space-y-4" @submit.prevent="submit">
    <h2 class="text-lg font-semibold">{{ t('auth.loginTitle') }}</h2>

    <div>
      <label class="label" for="email">{{ t('auth.email') }}</label>
      <input id="email" v-model="email" type="email" autocomplete="username" required class="input" />
    </div>

    <div>
      <label class="label" for="password">{{ t('auth.password') }}</label>
      <input id="password" v-model="password" type="password" autocomplete="current-password" required class="input" />
    </div>

    <p v-if="error" class="text-sm text-danger-600" role="alert">{{ error }}</p>

    <button type="submit" class="btn-primary w-full" :disabled="auth.loading">
      {{ auth.loading ? t('common.loading') : t('auth.submit') }}
    </button>
  </form>
</template>
