<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import PdfPageViewer from '@/components/PdfPageViewer.vue'
import type { DocumentJSON } from '@/types/documentJson'
import {
  extractOutlineFromDocument,
  extractOutlineFromText,
  type OutlineItem,
} from '@/types/documentJson'
import {
  isHeadingLineStart,
  isPageMarker,
  splitMixedHeadingLine,
} from '@/utils/headingDetect'

const props = withDefaults(
  defineProps<{
    modelValue: string
    sourceFile?: File | null
    previewUrl?: string | null
    fullTextRaw?: string | null
    documentJson?: DocumentJSON | null
    ocrUsed?: boolean
    ocrEngine?: string | null
    confidence?: number | null
    ocrNeedsReview?: boolean
    charCount?: number | null
    readonly?: boolean
    minRows?: number
    defaultReadingMode?: boolean
  }>(),
  {
    sourceFile: null,
    previewUrl: null,
    fullTextRaw: null,
    documentJson: null,
    ocrUsed: false,
    ocrEngine: null,
    confidence: null,
    ocrNeedsReview: false,
    charCount: null,
    readonly: false,
    minRows: 16,
    defaultReadingMode: true,
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const localPreviewUrl = ref<string | null>(null)
const pdfViewerRef = ref<InstanceType<typeof PdfPageViewer> | null>(null)
const activePage = ref(1)
const readingMode = ref(props.defaultReadingMode && props.readonly)
const contentTab = ref<'layout' | 'raw'>('layout')
const bodyRef = ref<HTMLElement | null>(null)
const outlineDrawerOpen = ref(false)
const showFullOutline = ref(false)
const ocrHintExpanded = ref(false)

const effectivePreviewUrl = computed(() => props.previewUrl || localPreviewUrl.value)

const showDualPane = computed(() => {
  if (!effectivePreviewUrl.value) return false
  if (props.sourceFile) {
    const ext = props.sourceFile.name.split('.').pop()?.toLowerCase() || ''
    return ext === 'pdf'
  }
  return Boolean(props.previewUrl)
})

const showRawTab = computed(
  () => Boolean(props.ocrUsed && props.fullTextRaw && props.fullTextRaw !== props.modelValue),
)

const displayText = computed(() => {
  if (contentTab.value === 'raw' && props.fullTextRaw) return props.fullTextRaw
  return props.modelValue
})

const content = computed({
  get: () => props.modelValue,
  set: (v: string) => emit('update:modelValue', v),
})

const outlineAll = computed<OutlineItem[]>(() => {
  if (props.documentJson?.pages?.length) {
    return extractOutlineFromDocument(props.documentJson)
  }
  return extractOutlineFromText(displayText.value)
})

const outline = computed(() => {
  if (showFullOutline.value) return outlineAll.value
  return outlineAll.value.filter((item) => item.page === activePage.value)
})

const qualityTags = computed(() => {
  const tags: string[] = []
  if (props.ocrUsed) tags.push('扫描件 OCR')
  if (props.ocrEngine) tags.push(props.ocrEngine)
  if (props.charCount != null) tags.push(`${props.charCount} 字`)
  if (props.confidence != null) tags.push(`置信度 ${Math.round(props.confidence * 100)}%`)
  return tags
})

function escapeHtml(text: string) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function renderBlockHtml(
  type: string,
  text: string,
  anchorId: string,
  pageNum?: number,
): string {
  const safe = escapeHtml(text)
  const anchorAttr = anchorId ? ` data-anchor="${escapeHtml(anchorId)}"` : ''
  if (type === 'page_marker') {
    const num = pageNum ?? text.match(/\d+/)?.[0] ?? ''
    return `<div class="page-marker"${anchorAttr} data-page="${num}">${safe}</div>`
  }
  if (type === 'heading') {
    return `<h4 class="clause-heading"${anchorAttr}>${safe}</h4>`
  }
  if (type === 'table') {
    return `<div class="table-row"${anchorAttr}>${safe}</div>`
  }
  if (!text.trim()) return '<br />'
  return `<p class="para"${anchorAttr}>${safe}</p>`
}

function htmlFromDocument(doc: DocumentJSON): string {
  const parts: string[] = []
  for (const page of doc.pages) {
    for (const block of page.blocks) {
      parts.push(
        renderBlockHtml(
          block.type,
          block.text,
          block.anchor_id || '',
          page.index + 1,
        ),
      )
    }
  }
  return parts.join('') || escapeHtml('（无正文）')
}

function htmlFromText(text: string): string {
  const parts: string[] = []
  let currentPage = 1
  let headingSeq = 0

  for (const line of text.split('\n')) {
    const trimmed = line.trim()
    if (isPageMarker(trimmed)) {
      const m = trimmed.match(/(\d+)/)
      if (m) currentPage = Number(m[1])
      parts.push(
        renderBlockHtml('page_marker', trimmed, `text-p${currentPage}-page`, currentPage),
      )
      continue
    }

    const split = splitMixedHeadingLine(trimmed)
    if (split) {
      headingSeq += 1
      const [headingText, body] = split
      parts.push(
        renderBlockHtml('heading', headingText, `text-p${currentPage}-h${headingSeq}`),
      )
      if (body) {
        parts.push(renderBlockHtml('paragraph', body, ''))
      }
      continue
    }

    if (isHeadingLineStart(trimmed)) {
      headingSeq += 1
      parts.push(
        renderBlockHtml('heading', trimmed, `text-p${currentPage}-h${headingSeq}`),
      )
      continue
    }

    if (trimmed.startsWith('|') || (trimmed.split(/\s{2,}/).length >= 3 && trimmed.length < 120)) {
      parts.push(renderBlockHtml('table', line, ''))
    } else if (!trimmed) {
      parts.push('<br />')
    } else {
      parts.push(renderBlockHtml('paragraph', line, ''))
    }
  }
  return parts.join('') || escapeHtml('（无正文）')
}

const readingHtml = computed(() => {
  if (props.documentJson?.pages?.length && contentTab.value === 'layout') {
    return htmlFromDocument(props.documentJson)
  }
  return htmlFromText(displayText.value || '（无正文）')
})

function scrollToAnchor(anchorId: string) {
  const root = bodyRef.value
  if (!root || !anchorId) return
  const el = root.querySelector(`[data-anchor="${anchorId}"]`)
  el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function scrollToOutline(item: OutlineItem) {
  activePage.value = item.page
  if (showDualPane.value && pdfViewerRef.value) {
    void pdfViewerRef.value.scrollToPage(item.page)
  }
  nextTick(() => {
    if (item.anchorId) {
      scrollToAnchor(item.anchorId)
      return
    }
    const root = bodyRef.value
    if (!root) return
    if (item.kind === 'page') {
      const marker = root.querySelector(`[data-page="${item.page}"]`)
      marker?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  })
}

function onPdfPageChange(page: number) {
  activePage.value = page
  nextTick(() => {
    const root = bodyRef.value
    const marker = root?.querySelector(`[data-page="${page}"]`)
    marker?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function revokeLocalUrl() {
  if (localPreviewUrl.value) {
    URL.revokeObjectURL(localPreviewUrl.value)
    localPreviewUrl.value = null
  }
}

watch(
  () => props.sourceFile,
  (file) => {
    revokeLocalUrl()
    if (!file) return
    const ext = file.name.split('.').pop()?.toLowerCase() || ''
    if (ext === 'pdf') {
      localPreviewUrl.value = URL.createObjectURL(file)
    }
  },
  { immediate: true },
)

watch(
  () => props.readonly,
  (ro) => {
    if (ro) readingMode.value = props.defaultReadingMode
  },
)

onBeforeUnmount(revokeLocalUrl)
</script>

<template>
  <div class="content-viewer">
    <div v-if="ocrUsed || qualityTags.length" class="content-viewer__toolbar">
      <div class="content-viewer__quality">
        <el-tag v-for="tag in qualityTags" :key="tag" size="small" type="info">{{ tag }}</el-tag>
        <el-tag v-if="ocrNeedsReview" size="small" type="warning">建议人工复核</el-tag>
      </div>
      <el-tabs v-if="showRawTab" v-model="contentTab" class="content-viewer__tabs-inline">
        <el-tab-pane label="排版后" name="layout" />
        <el-tab-pane label="OCR 原始" name="raw" />
      </el-tabs>
    </div>

    <div
      v-if="ocrUsed && showDualPane"
      class="content-viewer__hint-compact"
      @click="ocrHintExpanded = !ocrHintExpanded"
    >
      <el-text size="small" type="info">
        OCR 正文已按版面重排，请与左侧原文核对
        <span v-if="ocrHintExpanded">；表格/签章区域可能有偏差</span>
        <span class="content-viewer__hint-toggle">{{ ocrHintExpanded ? '收起' : '详情' }}</span>
      </el-text>
    </div>
    <el-alert
      v-else-if="ocrNeedsReview"
      type="warning"
      :closable="false"
      show-icon
      class="content-viewer__hint"
      title="部分页面识别置信度较低，请重点核对相对方、金额与条款"
    />

    <div class="content-viewer__main" :class="{ 'content-viewer__main--dual': showDualPane }">
      <aside v-if="showDualPane" class="content-viewer__preview">
        <div class="content-viewer__preview-label">原文预览</div>
        <PdfPageViewer
          ref="pdfViewerRef"
          :src="effectivePreviewUrl"
          :page="activePage"
          @update:page="onPdfPageChange"
        />
      </aside>

      <div class="content-viewer__body">
        <div class="content-viewer__body-header">
          <div class="content-viewer__body-actions">
            <el-button
              v-if="outlineAll.length"
              size="small"
              @click="outlineDrawerOpen = true"
            >
              目录 ({{ outlineAll.length }})
            </el-button>
            <el-switch
              v-if="outlineAll.length"
              v-model="showFullOutline"
              size="small"
              inline-prompt
              active-text="全文"
              inactive-text="当前页"
              style="margin-left: 8px"
            />
          </div>
          <div v-if="!readonly" class="content-viewer__mode-bar">
            <el-radio-group v-model="readingMode" size="small">
              <el-radio-button :label="true">阅读</el-radio-button>
              <el-radio-button :label="false">编辑</el-radio-button>
            </el-radio-group>
          </div>
        </div>

        <div ref="bodyRef" class="content-viewer__scroll">
          <template v-if="readonly || readingMode">
            <article class="content-viewer__article" v-html="readingHtml" />
          </template>
          <template v-else>
            <el-input
              v-model="content"
              type="textarea"
              :rows="minRows"
              class="content-viewer__textarea"
              placeholder="合同正文"
            />
          </template>
        </div>
      </div>
    </div>

    <el-drawer
      v-model="outlineDrawerOpen"
      title="目录"
      direction="ltr"
      size="280px"
      append-to-body
    >
      <ul class="content-viewer__outline-list">
        <li
          v-for="item in (showFullOutline ? outlineAll : outline)"
          :key="item.anchorId"
          :class="[
            'content-viewer__outline-item',
            `content-viewer__outline-item--${item.kind}`,
            {
              'is-warn': item.needs_review,
              'is-active': item.page === activePage && item.kind === 'page',
            },
          ]"
          @click="scrollToOutline(item); outlineDrawerOpen = false"
        >
          {{ item.label }}
          <span v-if="item.llm_corrected" class="content-viewer__badge">AI 补正</span>
        </li>
      </ul>
    </el-drawer>
  </div>
</template>

<style scoped>
.content-viewer {
  width: 100%;
}
.content-viewer__toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 10px;
}
.content-viewer__quality {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.content-viewer__tabs-inline {
  margin: 0;
}
.content-viewer__tabs-inline :deep(.el-tabs__header) {
  margin: 0;
}
.content-viewer__hint-compact {
  margin-bottom: 10px;
  cursor: pointer;
  user-select: none;
}
.content-viewer__hint-toggle {
  margin-left: 6px;
  color: #0369a1;
}
.content-viewer__hint {
  margin-bottom: 12px;
}
.content-viewer__main {
  display: grid;
  gap: 16px;
  align-items: start;
}
.content-viewer__main--dual {
  grid-template-columns: minmax(300px, 38%) 1fr;
}
.content-viewer__preview {
  min-width: 320px;
  max-width: 420px;
}
.content-viewer__preview-label {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 8px;
}
.content-viewer__body {
  min-width: 0;
  flex: 1;
}
.content-viewer__body-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
.content-viewer__body-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}
.content-viewer__outline-list {
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 13px;
}
.content-viewer__outline-item {
  padding: 8px 10px;
  border-radius: 4px;
  cursor: pointer;
  color: #374151;
  line-height: 1.45;
}
.content-viewer__outline-item:hover {
  background: #f3f4f6;
}
.content-viewer__outline-item--heading {
  padding-left: 20px;
}
.content-viewer__outline-item.is-warn {
  color: #b45309;
}
.content-viewer__outline-item.is-active {
  background: #e0f2fe;
  color: #0369a1;
}
.content-viewer__badge {
  margin-left: 4px;
  font-size: 10px;
  color: #7c3aed;
}
.content-viewer__scroll {
  max-height: min(72vh, 640px);
  overflow: auto;
}
.content-viewer__textarea :deep(textarea) {
  line-height: 1.75;
  font-family: inherit;
}
.content-viewer__article {
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fafafa;
  line-height: 1.75;
}
.content-viewer__article :deep(.page-marker) {
  display: block;
  margin: 12px 0 8px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 600;
  color: #0369a1;
  background: #e0f2fe;
  border-radius: 4px;
}
.content-viewer__article :deep(.clause-heading) {
  margin: 16px 0 8px;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}
.content-viewer__article :deep(.table-row) {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  background: #f3f4f6;
  padding: 2px 6px;
  margin: 2px 0;
  border-radius: 2px;
}
.content-viewer__article :deep(.para) {
  margin: 0 0 8px;
}
@media (max-width: 900px) {
  .content-viewer__main--dual {
    grid-template-columns: 1fr;
  }
  .content-viewer__preview {
    max-width: none;
  }
}
</style>
