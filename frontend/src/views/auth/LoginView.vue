<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { client, setToken } from '@/api/client'
import { ROLE_LABELS } from '@/api/config'
import { useAuthStore } from '@/stores/auth'
import type { AppRole } from '@/types/models'

const router = useRouter()
const auth = useAuthStore()
const username = ref('drafter1')
const password = ref('123456')
const loading = ref(false)

const demoRoles = Object.entries(ROLE_LABELS).map(([value, label]) => ({
  value: value as AppRole,
  label,
}))

async function login() {
  loading.value = true
  try {
    const q = new URLSearchParams({ username: username.value, password: password.value })
    const data = await client.post<{ token: string; user: { id: number; username: string } }>(
      `/api/v1/system/login?${q.toString()}`,
    )
    setToken(data.token)
    sessionStorage.setItem('api_current_user', JSON.stringify(data.user))
    auth.user = data.user as import('@/types/models').ApiUser
    ElMessage.success(`欢迎，${data.user.username}`)
    router.push({ name: 'dashboard' })
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '登录失败')
  } finally {
    loading.value = false
  }
}

async function quickLoginAs(role: AppRole) {
  loading.value = true
  try {
    await auth.switchRole(role)
    ElMessage.success(`已切换为 ${ROLE_LABELS[role]}`)
    router.push({ name: 'dashboard' })
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '演示登录失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (auth.user) router.replace({ name: 'dashboard' })
})
</script>

<template>
  <div class="login-page">
    <el-card class="login-card" shadow="hover">
      <h2>合同审批平台</h2>
      <p class="hint">演示账号：drafter1 / 123456</p>
      <el-form label-width="72px" @submit.prevent="login">
        <el-form-item label="用户名">
          <el-input v-model="username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" autocomplete="current-password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="login">登录</el-button>
        </el-form-item>
      </el-form>
      <div class="demo-roles">
        <p class="demo-title">演示快捷登录（进入看板后也可右上角切换）</p>
        <div class="demo-role-grid">
          <el-button
            v-for="item in demoRoles"
            :key="item.value"
            size="small"
            :loading="loading"
            @click="quickLoginAs(item.value)"
          >
            {{ item.label }}
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
}
.login-card {
  width: 400px;
}
.hint {
  color: #6b7280;
  font-size: 13px;
  margin: 0 0 16px;
}
.demo-roles {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}
.demo-title {
  margin: 0 0 12px;
  font-size: 13px;
  color: #6b7280;
}
.demo-role-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
