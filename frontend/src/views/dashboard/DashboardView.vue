<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { contractsApi } from '@/api/contracts'

const router = useRouter()
const loading = ref(true)
const stats = ref({ pending_approval: 0, in_review: 0, sealed_or_archived: 0 })

onMounted(async () => {
  try {
    const data = await contractsApi.dashboard()
    stats.value = {
      pending_approval: Number(data.pending_approval ?? 0),
      in_review: Number(data.in_review ?? 0),
      sealed_or_archived: Number(data.sealed_or_archived ?? 0),
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

function go(name: string) {
  router.push({ name })
}
</script>

<template>
  <div v-loading="loading">
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card" @click="go('approvals')">
          <div class="stat-label">待审批</div>
          <div class="stat-value">{{ stats.pending_approval }}</div>
          <p class="stat-hint">点击进入待办审批</p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card" @click="go('review-center')">
          <div class="stat-label">评审中</div>
          <div class="stat-value">{{ stats.in_review }}</div>
          <p class="stat-hint">点击进入评审中心</p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card" @click="go('archives')">
          <div class="stat-label">已用印/归档</div>
          <div class="stat-value">{{ stats.sealed_or_archived }}</div>
          <p class="stat-hint">点击查看归档台账</p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.stat-card {
  cursor: pointer;
  transition: transform 0.15s ease;
}
.stat-card:hover {
  transform: translateY(-2px);
}
.stat-label {
  color: #6b7280;
  font-size: 13px;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  margin-top: 8px;
  color: #1d4ed8;
}
.stat-hint {
  color: #9ca3af;
  font-size: 12px;
  margin: 8px 0 0;
}
</style>
