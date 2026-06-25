<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { client } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
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
    <div class="login-bg">
      <div class="bg-orb bg-orb-1" />
      <div class="bg-orb bg-orb-2" />
      <div class="bg-orb bg-orb-3" />
    </div>

    <div class="login-container">
      <!-- 品牌区 -->
      <div class="login-brand">
        <div class="brand-logo">
          <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="40" height="40" rx="10" fill="#1d4ed8" />
            <text x="20" y="27" text-anchor="middle" fill="#fff" font-size="18" font-weight="700" font-family="system-ui, -apple-system, sans-serif">合</text>
          </svg>
        </div>
        <h1 class="brand-title">合同审批平台</h1>
        <p class="brand-sub">Contract Lifecycle Management</p>
      </div>

      <!-- 登录卡片 -->
      <div class="login-card">
        <form class="login-form" @submit.prevent="login">
          <div class="field-group">
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
          </div>

          <button class="login-btn" type="submit" :disabled="loading">
            <span v-if="loading" class="spinner" />
            <span>{{ loading ? '登录中...' : '登 录' }}</span>
          </button>
        </form>
      </div>

      <!-- 底部 -->
      <div class="login-footer">
        <span>&copy; 2026 合同审批平台</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0f172a;
  position: relative;
  overflow: hidden;
}

/* 动态背景 */
.login-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.35;
}

.bg-orb-1 {
  width: 600px;
  height: 600px;
  background: #1d4ed8;
  top: -200px;
  right: -100px;
  animation: drift1 20s ease-in-out infinite;
}

.bg-orb-2 {
  width: 400px;
  height: 400px;
  background: #7c3aed;
  bottom: -100px;
  left: -50px;
  animation: drift2 16s ease-in-out infinite;
}

.bg-orb-3 {
  width: 300px;
  height: 300px;
  background: #0ea5e9;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  opacity: 0.2;
  animation: drift3 24s ease-in-out infinite;
}

@keyframes drift1 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-60px, 40px); }
}

@keyframes drift2 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(40px, -50px); }
}

@keyframes drift3 {
  0%, 100% { transform: translate(-50%, -50%) scale(1); }
  50% { transform: translate(-50%, -50%) scale(1.2); }
}

.login-container {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
  width: 400px;
  max-width: 90vw;
}

/* 品牌区 */
.login-brand {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.brand-logo svg {
  width: 48px;
  height: 48px;
  filter: drop-shadow(0 4px 12px rgba(29, 78, 216, 0.4));
}

.brand-title {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  margin: 0;
  letter-spacing: 1px;
}

.brand-sub {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
  margin: 0;
  letter-spacing: 2px;
  text-transform: uppercase;
}

/* 登录卡片 */
.login-card {
  width: 100%;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  padding: 40px 36px;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: block;
  position: relative;
}

.field-input {
  width: 100%;
  padding: 14px 16px;
  font-size: 15px;
  color: #fff;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  outline: none;
  transition: all 0.2s ease;
  font-family: inherit;
}

.field-input::placeholder {
  color: rgba(255, 255, 255, 0.35);
}

.field-input:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.2);
}

.field-input:focus {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(96, 165, 250, 0.6);
  box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.15);
}

/* 登录按钮 */
.login-btn {
  width: 100%;
  padding: 14px 24px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #1d4ed8, #3b82f6);
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  letter-spacing: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 8px;
}

.login-btn:hover {
  background: linear-gradient(135deg, #2563eb, #60a5fa);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.4);
  transform: translateY(-1px);
}

.login-btn:active {
  transform: translateY(0);
}

.login-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
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

/* 底部 */
.login-footer {
  text-align: center;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.25);
}

/* 响应式 */
@media (max-width: 480px) {
  .login-container {
    width: 100%;
    padding: 24px;
  }

  .login-card {
    padding: 32px 24px;
    border-radius: 16px;
  }

  .brand-title {
    font-size: 24px;
  }
}
</style>
