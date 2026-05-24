<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { configApi, type ThresholdsConfig } from '@/api/config'
import { approvalsApi } from '@/api/approvals'
import { contractsApi } from '@/api/contracts'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const form = reactive<ThresholdsConfig>({
  simple_max: 100000,
  standard_max: 1000000,
  board_threshold: 1000000,
})
const loading = ref(false)
const saving = ref(false)
const devOpen = ref<string[]>([])
const historySteps = ref(0)

onMounted(async () => {
  loading.value = true
  try {
    const data = await configApi.getThresholds()
    Object.assign(form, data)
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})

async function save() {
  saving.value = true
  try {
    await auth.switchRole('admin')
    const data = await configApi.updateThresholds({ ...form })
    Object.assign(form, data)
    ElMessage.success('阈值已保存')
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

async function runDemo03() {
  loading.value = true
  try {
    await auth.switchRole('drafter')
    const c = await contractsApi.create({
      title: 'Vue DEMO-03 大额合同',
      contract_type: 'purchase',
      counterparty_name: '大客户',
      amount: 2500000,
      content: '大额采购',
    })
    const flow = await approvalsApi.submit(c.id, 'large_amount')
    const hist = await approvalsApi.history(flow.flow_id)
    historySteps.value = hist.total_steps || 0
    ElMessage.success(`DEMO-03：审批历史 ${historySteps.value} 步`)
    auth.setLastContract(c, flow.flow_id)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : 'DEMO-03 失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div v-loading="loading" class="page-card">
    <div class="page-toolbar">
      <h2>审批配置</h2>
      <el-button type="primary" :loading="saving" @click="save">保存阈值</el-button>
    </div>
    <el-form label-width="160px" style="max-width: 520px">
      <el-form-item label="简易流程上限（元）">
        <el-input-number v-model="form.simple_max" :min="0" :step="10000" style="width: 100%" />
      </el-form-item>
      <el-form-item label="标准流程上限（元）">
        <el-input-number v-model="form.standard_max" :min="0" :step="100000" style="width: 100%" />
      </el-form-item>
      <el-form-item label="董事会阈值（元）">
        <el-input-number v-model="form.board_threshold" :min="0" :step="100000" style="width: 100%" />
      </el-form-item>
    </el-form>
    <el-collapse v-model="devOpen" style="margin-top: 24px; max-width: 640px">
      <el-collapse-item title="开发者工具（DEMO-03）" name="dev">
        <el-button :loading="loading" @click="runDemo03">运行 DEMO-03 特殊流程</el-button>
        <p v-if="historySteps" style="margin-top: 8px; color: #6b7280">最近历史步数：{{ historySteps }}</p>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>
