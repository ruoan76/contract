<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { client } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { BRAND } from '@/constants/brand'
import BrandIcon from '@/components/BrandIcon.vue'
import type { ApiUser } from '@/types/models'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const username = ref('')
const password = ref('')
const loading = ref(false)

async function login() {
  if (!username.value.trim()) {
    ElMessage.warning('请输入用户名')
    return
  }
  loading.value = true
  try {
    const q = new URLSearchParams({ username: username.value, password: password.value })
    const data = await client.post<{
      token: string
      user: ApiUser & { role_code?: string }
    }>(`/api/v1/system/login?${q.toString()}`)
    await auth.completeLogin(data.token, data.user)
    ElMessage.success(`欢迎，${data.user.real_name || data.user.username}`)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    if (redirect && redirect.startsWith('/')) {
      await router.push(redirect)
    } else {
      await router.push({ name: 'dashboard' })
    }
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '登录失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (auth.user && auth.role) router.replace({ name: 'dashboard' })
})
</script>

<template>
  <div class="login-page">
    <main class="login-sheet">
      <header class="login-hero">
        <BrandIcon :size="52" class="login-hero-icon" />
        <h1 class="login-title">
          <span class="login-title-cn">浪潮</span>
          <span class="login-title-en">inContract</span>
        </h1>
        <p class="login-tagline">{{ BRAND.loginTagline }}</p>
      </header>

      <form class="login-form" @submit.prevent="login">
        <label class="field" for="username">
          <input
            id="username"
            v-model="username"
            class="field-input"
            type="text"
            placeholder="用户名"
            autocomplete="username"
            autofocus
          />
        </label>
        <label class="field" for="password">
          <input
            id="password"
            v-model="password"
            class="field-input"
            type="password"
            placeholder="密码"
            autocomplete="current-password"
          />
        </label>
        <button class="login-btn" type="submit" :disabled="loading">
          <span v-if="loading" class="spinner" aria-hidden="true" />
          <span>{{ loading ? '登录中...' : '登录' }}</span>
        </button>
      </form>

      <footer class="login-footer">
        <span>{{ BRAND.copyright }}</span>
        <span class="login-footer-slogan">{{ BRAND.slogan }}</span>
      </footer>
    </main>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: radial-gradient(ellipse at 50% 0%, rgba(0, 102, 204, 0.18) 0%, #0a1020 55%);
}

.login-sheet {
  width: 100%;
  max-width: 360px;
  padding: 48px 40px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.login-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  margin-bottom: 32px;
}

.login-hero-icon {
  margin-bottom: 16px;
}

.login-title {
  margin: 0;
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.login-title-cn {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 2px;
}

.login-title-en {
  font-size: 20px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
}

.login-tagline {
  margin: 8px 0 0;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.55);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: block;
}

.field-input {
  width: 100%;
  height: 48px;
  padding: 0 16px;
  font-size: 15px;
  color: #fff;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  outline: none;
  transition: border-color 0.15s ease, background 0.15s ease;
  font-family: inherit;
  box-sizing: border-box;
}

.field-input::placeholder {
  color: rgba(255, 255, 255, 0.42);
}

.field-input:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.16);
}

.field-input:focus {
  background: rgba(255, 255, 255, 0.08);
  border-color: var(--primary-light);
}

.login-btn {
  width: 100%;
  height: 48px;
  margin-top: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background: var(--primary);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.login-btn:hover:not(:disabled) {
  background: var(--primary-dark);
}

.login-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.login-footer {
  margin-top: 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
  text-align: center;
}

.login-footer-slogan {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.28);
  letter-spacing: 1px;
}

@media (max-width: 480px) {
  .login-sheet {
    padding: 40px 28px;
  }

  .login-title-cn {
    font-size: 24px;
  }

  .login-title-en {
    font-size: 18px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation: none;
  }
}
</style>
