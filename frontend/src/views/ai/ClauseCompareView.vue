<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { clauseCompareApi, type ClauseCompareResult } from '@/api/clause-compare'

const leftText = ref('甲方应在合同签订后 30 日内支付全款。')
const rightText = ref('甲方应在合同签订后 45 日内支付全款。')
const loading = ref(false)
const result = ref<ClauseCompareResult | null>(null)

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
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>条款比对</h2>
      <el-button type="primary" :loading="loading" @click="runCompare">开始比对</el-button>
    </div>
    <el-row :gutter="16">
      <el-col :span="12">
        <p class="label">基准版</p>
        <el-input v-model="leftText" type="textarea" :rows="10" />
      </el-col>
      <el-col :span="12">
        <p class="label">对比版</p>
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
