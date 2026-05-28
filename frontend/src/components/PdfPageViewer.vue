<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker

const props = withDefaults(
  defineProps<{
    src: string | null
    /** 1-based 页码 */
    page?: number
  }>(),
  { page: 1 },
)

const emit = defineEmits<{
  'update:page': [page: number]
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const loading = ref(false)
const errorMsg = ref('')
const totalPages = ref(0)
const currentPage = ref(props.page || 1)

let pdfDoc: pdfjsLib.PDFDocumentProxy | null = null
let renderTask: pdfjsLib.RenderTask | null = null

async function loadPdf(url: string) {
  loading.value = true
  errorMsg.value = ''
  try {
    if (pdfDoc) {
      await pdfDoc.destroy()
      pdfDoc = null
    }
    const task = pdfjsLib.getDocument(url)
    pdfDoc = await task.promise
    totalPages.value = pdfDoc.numPages
    const target = Math.min(Math.max(currentPage.value, 1), totalPages.value || 1)
    currentPage.value = target
    await renderPage(target)
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : 'PDF 加载失败'
  } finally {
    loading.value = false
  }
}

async function renderPage(pageNum: number) {
  if (!pdfDoc || !canvasRef.value) return
  if (renderTask) {
    try {
      await renderTask.cancel()
    } catch {
      /* 忽略取消 */
    }
  }
  const page = await pdfDoc.getPage(pageNum)
  const viewport = page.getViewport({ scale: 1.2 })
  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  canvas.height = viewport.height
  canvas.width = viewport.width
  renderTask = page.render({ canvasContext: ctx, viewport })
  await renderTask.promise
  renderTask = null
}

function goPage(delta: number) {
  if (!totalPages.value) return
  const next = Math.min(Math.max(currentPage.value + delta, 1), totalPages.value)
  if (next === currentPage.value) return
  currentPage.value = next
  emit('update:page', next)
  void renderPage(next)
}

watch(
  () => props.src,
  (url) => {
    if (url) void loadPdf(url)
  },
  { immediate: true },
)

watch(
  () => props.page,
  (p) => {
    if (!p || p === currentPage.value || !pdfDoc) return
    currentPage.value = p
    void renderPage(p)
  },
)

onBeforeUnmount(async () => {
  if (renderTask) {
    try {
      await renderTask.cancel()
    } catch {
      /* 忽略 */
    }
  }
  if (pdfDoc) {
    await pdfDoc.destroy()
  }
})

defineExpose({
  scrollToPage: async (page: number) => {
    if (!pdfDoc) return
    currentPage.value = page
    await nextTick()
    await renderPage(page)
    emit('update:page', page)
  },
})
</script>

<template>
  <div class="pdf-viewer" v-loading="loading">
    <div v-if="errorMsg" class="pdf-viewer__error">{{ errorMsg }}</div>
    <div v-else class="pdf-viewer__canvas-wrap">
      <canvas ref="canvasRef" class="pdf-viewer__canvas" />
    </div>
    <div v-if="totalPages > 0" class="pdf-viewer__toolbar">
      <el-button size="small" :disabled="currentPage <= 1" @click="goPage(-1)">上一页</el-button>
      <span class="pdf-viewer__page-info">{{ currentPage }} / {{ totalPages }}</span>
      <el-button size="small" :disabled="currentPage >= totalPages" @click="goPage(1)">下一页</el-button>
    </div>
  </div>
</template>

<style scoped>
.pdf-viewer {
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f9fafb;
  overflow: hidden;
}
.pdf-viewer__canvas-wrap {
  max-height: min(72vh, 640px);
  overflow: auto;
  display: flex;
  justify-content: center;
  padding: 8px;
}
.pdf-viewer__canvas {
  max-width: 100%;
  height: auto;
}
.pdf-viewer__toolbar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 8px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}
.pdf-viewer__page-info {
  font-size: 13px;
  color: #6b7280;
  min-width: 72px;
  text-align: center;
}
.pdf-viewer__error {
  padding: 16px;
  color: #dc2626;
  font-size: 13px;
}
</style>
