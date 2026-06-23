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
    <el-card class="login-card" shadow="hover">
      <h2>合同审批平台</h2>
      <p class="hint">请使用企业账号登录</p>
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
</style>
