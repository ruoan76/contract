<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
const title = route.meta.title as string
</script>

<template>
  <div class="page-card">
    <el-empty :description="`${title || '该页面'} — V1.1 规划中`">
      <p class="hint">当前 Sprint 聚焦 DEMO 主路径页面，此功能稍后实现。</p>
    </el-empty>
  </div>
</template>

<style scoped>
.hint {
  color: #6b7280;
  font-size: 13px;
  margin-top: 8px;
}
</style>
