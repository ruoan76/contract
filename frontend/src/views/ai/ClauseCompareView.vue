<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { clauseCompareApi, type ClauseCompareResult } from '@/api/clause-compare'
import { contractsApi } from '@/api/contracts'
import { useContractContext } from '@/composables/useContractContext'
import ContractContextBar from '@/components/ContractContextBar.vue'
import type { Contract } from '@/types/models'

const router = useRouter()
const { contractId, fetchContract } = useContractContext()
const contract = ref<Contract | null>(null)
const inputMode = ref<'paste' | 'upload'>('paste')
const leftText = ref('')
const rightText = ref('')
const loading = ref(false)
const result = ref<ClauseCompareResult | null>(null)

async function loadContractTexts() {
  const id = contractId.value
  if (!id) return
  try {
    contract.value = await fetchContract(id)
    const versions = (await contractsApi.listVersions(id)) || []
    const sorted = [...versions].sort((a, b) => (b.version || 0) - (a.version || 0))
    const current = sorted[0]
    const previous = sorted[1]
    leftText.value =
      (previous?.content || '').trim() ||
      '（无上一版本，可粘贴基准文本）'
    rightText.value =
      (current?.content || contract.value?.content || '').trim() ||
      '（无当前版本正文）'
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  if (!contractId.value) {
    router.replace({ name: 'contracts' })
    return
  }
  loadContractTexts()
})

watch(contractId, () => {
  if (contractId.value) loadContractTexts()
})

async function runCompare() {
  if (!leftText.value.trim() || !rightText.value.trim()) {
    ElMessage.warning('请填写两段比对文本')
    return
  }
  loading.value = true
  try {
    result.value = await clauseCompareApi.compare(leftText.value, rightText.value)
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '比对失败')
  } finally {
    loading.value = false
  }
}

function readFileAsText(file: File, target: 'left' | 'right') {
  const reader = new FileReader()
  reader.onload = () => {
    const text = String(reader.result || '')
    if (target === 'left') leftText.value = text
    else rightText.value = text
    ElMessage.success('文件已载入')
  }
  reader.onerror = () => ElMessage.error('读取文件失败')
  reader.readAsText(file, 'utf-8')
  return false
}
</script>

<template>
  <div class="page-card">
    <ContractContextBar :contract="contract" />
    <div class="page-toolbar">
      <div>
        <h2>条款比对</h2>
        <p class="hint">对比上一版本与当前版本正文，辅助法务发现修订差异。</p>
      </div>
      <el-button type="primary" :loading="loading" @click="runCompare">开始比对</el-button>
    </div>

    <el-radio-group v-model="inputMode" style="margin-bottom: 16px">
      <el-radio-button value="paste">粘贴文本</el-radio-button>
      <el-radio-button value="upload">上传 TXT</el-radio-button>
    </el-radio-group>

    <el-row :gutter="16">
      <el-col :span="12">
        <p class="label">基准版（通常为上一版本）</p>
        <el-upload
          v-if="inputMode === 'upload'"
          :auto-upload="true"
          :show-file-list="false"
          accept=".txt,text/plain"
          :before-upload="(f: File) => readFileAsText(f, 'left')"
        >
          <el-button size="small">上传基准 TXT</el-button>
        </el-upload>
        <el-input v-model="leftText" type="textarea" :rows="10" />
      </el-col>
      <el-col :span="12">
        <p class="label">对比版（当前版本）</p>
        <el-upload
          v-if="inputMode === 'upload'"
          :auto-upload="true"
          :show-file-list="false"
          accept=".txt,text/plain"
          :before-upload="(f: File) => readFileAsText(f, 'right')"
        >
          <el-button size="small">上传对比 TXT</el-button>
        </el-upload>
        <el-input v-model="rightText" type="textarea" :rows="10" />
      </el-col>
    </el-row>
    <div v-if="result" class="result-panel">
      <p>相似度：{{ result.similarity_percent }}% · 差异块：{{ result.change_count }}</p>
      <el-scrollbar max-height="240px">
        <pre class="diff">{{ (result.diff_lines || []).join('\n') }}</pre>
      </el-scrollbar>
    </div>
  </div>
</template>

<style scoped>
.page-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  gap: 16px;
}
.hint {
  margin: 4px 0 0;
  font-size: 13px;
  color: #6b7280;
}
.label {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 8px;
}
.result-panel {
  margin-top: 20px;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
}
.diff {
  font-size: 12px;
  white-space: pre-wrap;
  margin: 0;
}
</style>
