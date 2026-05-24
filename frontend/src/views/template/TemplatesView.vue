<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { templatesApi, type ContractTemplate } from '@/api/templates'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const loading = ref(true)
const items = ref<ContractTemplate[]>([])
const dialogVisible = ref(false)
const form = reactive({ name: '', category: 'purchase', content: '' })

const STATUS_MAP: Record<string, string> = {
  draft: '草稿',
  pending_publish: '待发布',
  published: '已发布',
  deprecated: '已废止',
}

async function load() {
  loading.value = true
  try {
    const res = await templatesApi.list({ page: 1, page_size: 50 })
    items.value = res.items || []
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function createTemplate() {
  if (!form.name.trim()) {
    ElMessage.warning('请填写模板名称')
    return
  }
  try {
    await auth.switchRole('admin')
    await templatesApi.create({ ...form })
    ElMessage.success('模板已创建')
    dialogVisible.value = false
    form.name = ''
    form.content = ''
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '创建失败')
  }
}

async function publish(row: ContractTemplate) {
  try {
    await auth.switchRole('admin')
    await templatesApi.publish(row.id)
    ElMessage.success('模板已发布')
    await load()
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : '发布失败')
  }
}
</script>

<template>
  <div class="page-card">
    <div class="page-toolbar">
      <h2>模板管理</h2>
      <el-button type="primary" @click="dialogVisible = true">新建模板</el-button>
    </div>
    <el-table v-loading="loading" :data="items" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="名称" min-width="160" />
      <el-table-column prop="category" label="分类" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ STATUS_MAP[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="version" label="版本" width="70" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button
            v-if="row.status !== 'published'"
            link
            type="primary"
            @click="publish(row)"
          >
            发布
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !items.length" description="暂无模板，请新建" />

    <el-dialog v-model="dialogVisible" title="新建模板" width="560px">
      <el-form label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="form.category" style="width: 100%">
            <el-option label="采购" value="purchase" />
            <el-option label="销售" value="sales" />
            <el-option label="服务" value="service" />
            <el-option label="劳动" value="labor" />
          </el-select>
        </el-form-item>
        <el-form-item label="正文">
          <el-input v-model="form.content" type="textarea" :rows="6" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createTemplate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
