<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { counterpartiesApi, type CounterpartyItem } from '@/api/counterparties'
import { contractsApi } from '@/api/contracts'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const items = ref<CounterpartyItem[]>([])
const loading = ref(false)
const name = ref('')
const creditCode = ref('')

async function load() {
  loading.value = true
  try {
    const res = await counterpartiesApi.list()
    items.value = res.items || []
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function createCounterparty() {
  loading.value = true
  try {
    await auth.switchRole('admin')
    const suffix = Date.now()
    await counterpartiesApi.create({
      name: name.value || `新公司${suffix}`,
      credit_code: creditCode.value || `91110000${String(suffix).slice(-8)}`,
    })
    ElMessage.success('相对方已创建')
    name.value = ''
    creditCode.value = ''
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '创建失败')
  } finally {
    loading.value = false
  }
}

async function blacklist(row: CounterpartyItem) {
  loading.value = true
  try {
    await auth.switchRole('admin')
    await counterpartiesApi.blacklist(row.id, '黑名单')
    ElMessage.success('已加入黑名单')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '操作失败')
  } finally {
    loading.value = false
  }
}

async function testBlockedCreate(row: CounterpartyItem) {
  try {
    await auth.switchRole('drafter')
    await contractsApi.create({
      title: '黑名单测试',
      contract_type: 'purchase',
      counterparty_name: row.name,
      amount: 100000,
      content: '应被拒绝',
    })
    ElMessage.error('预期应返回 403')
  } catch (e) {
    ElMessage.success(`创建被拒绝：${e instanceof Error ? e.message : ''}`)
  }
}
</script>

<template>
  <div class="page-card">
    <h2>相对方管理</h2>
    <el-form inline style="margin: 16px 0">
      <el-form-item label="名称">
        <el-input v-model="name" placeholder="新公司名" />
      </el-form-item>
      <el-form-item label="信用代码">
        <el-input v-model="creditCode" placeholder="可选" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" @click="createCounterparty">新增</el-button>
      </el-form-item>
    </el-form>
    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="credit_code" label="信用代码" min-width="180" />
      <el-table-column label="黑名单" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_blacklisted ? 'danger' : 'success'" size="small">
            {{ row.is_blacklisted ? '是' : '否' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="danger" :disabled="!!row.is_blacklisted" @click="blacklist(row)">
            拉黑
          </el-button>
          <el-button v-if="row.is_blacklisted" link @click="testBlockedCreate(row)">测试拒绝</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
