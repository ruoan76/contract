<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { contractsApi } from '@/api/contracts'
import { reviewsApi } from '@/api/reviews'
import { aiReviewApi } from '@/api/ai-review'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const contractId = ref<number>(0)
const content = ref('')
const changeDesc = ref('修改条款')
const submitting = ref(false)

function resolveId(): number {
  return Number(route.params.id) || auth.restoreLastContractId() || auth.lastContract?.id || 0
}

async function load() {
  contractId.value = resolveId()
  if (!contractId.value) return
  try {
    const c = await contractsApi.get(contractId.value)
    content.value = c.content || ''
  } catch (e) {
    console.error(e)
  }
}

onMounted(load)
watch(() => route.params.id, load)

async function submitRevision() {
  if (!contractId.value) {
    ElMessage.warning('无合同上下文')
    return
  }
  submitting.value = true
  try {
    await auth.switchRole('drafter')
    const rev = await contractsApi.submitRevision(contractId.value, {
      content: content.value,
      change_description: changeDesc.value,
    })
    await aiReviewApi.review(contractId.value)
    ElMessage.success(`修订已提交，版本 v${rev.version || 2}`)
    router.push({ name: 'contract-detail', params: { id: contractId.value } })
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '修订失败')
  } finally {
    submitting.value = false
  }
}

async function requestReturn() {
  if (!contractId.value) return
  try {
    await auth.switchRole('legal')
    await reviewsApi.returnForRevision(contractId.value, 'legal', '请修改条款')
    ElMessage.success('已退回修订')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '退回失败')
  }
}
</script>

<template>
  <div class="page-card">
    <h2>修订工作台 · 合同 #{{ contractId || '—' }}</h2>
    <el-form label-width="100px" style="max-width: 720px; margin-top: 16px">
      <el-form-item label="修订说明">
        <el-input v-model="changeDesc" />
      </el-form-item>
      <el-form-item label="合同正文">
        <el-input v-model="content" type="textarea" :rows="8" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="submitting" @click="submitRevision">提交修订</el-button>
        <el-button @click="requestReturn">模拟法务退回</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>
