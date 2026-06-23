import {
  isHeadingLineStart,
  isPageMarker,
  outlineLabelForLine,
  parsePageNumber,
  splitMixedHeadingLine,
} from '@/utils/headingDetect'

export type DocumentBlockType = 'paragraph' | 'heading' | 'table' | 'page_marker'

export interface DocumentBlock {
  type: DocumentBlockType
  text: string
  bbox?: number[][] | null
  anchor_id?: string | null
  outline_label?: string | null
}

export interface DocumentPage {
  index: number
  source: 'ocr' | 'native'
  avg_confidence?: number | null
  needs_review?: boolean
  llm_corrected?: boolean
  layout_suspect?: boolean
  blocks: DocumentBlock[]
}

export interface DocumentJSON {
  version: string
  pages: DocumentPage[]
}

export interface OutlineItem {
  kind: 'page' | 'heading'
  page: number
  label: string
  anchorId: string
  needs_review?: boolean
  llm_corrected?: boolean
}

export function extractOutlineFromDocument(doc: DocumentJSON | null | undefined): OutlineItem[] {
  if (!doc?.pages?.length) return []
  const outline: OutlineItem[] = []
  for (const page of doc.pages) {
    for (const block of page.blocks) {
      if (block.type === 'page_marker') {
        const pageNum = parsePageNumber(block.text) ?? page.index + 1
        outline.push({
          kind: 'page',
          page: pageNum,
          label: block.outline_label?.trim() || block.text.trim(),
          anchorId: block.anchor_id || `p${pageNum}-marker`,
          needs_review: page.needs_review,
          llm_corrected: page.llm_corrected,
        })
      } else if (block.type === 'heading') {
        outline.push({
          kind: 'heading',
          page: page.index + 1,
          label: (block.outline_label || block.text).trim().slice(0, 80),
          anchorId: block.anchor_id || `p${page.index + 1}-h-${outline.length}`,
          needs_review: page.needs_review,
        })
      }
    }
  }
  return outline
}

export function extractOutlineFromText(text: string): OutlineItem[] {
  const outline: OutlineItem[] = []
  let currentPage = 1
  let headingSeq = 0

  for (const line of text.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed) continue

    if (isPageMarker(trimmed)) {
      const pageNum = parsePageNumber(trimmed)
      if (pageNum != null) currentPage = pageNum
      outline.push({
        kind: 'page',
        page: currentPage,
        label: trimmed,
        anchorId: `text-p${currentPage}-page`,
      })
      continue
    }

    const split = splitMixedHeadingLine(trimmed)
    if (split) {
      headingSeq += 1
      outline.push({
        kind: 'heading',
        page: currentPage,
        label: split[0].slice(0, 80),
        anchorId: `text-p${currentPage}-h${headingSeq}`,
      })
    } else if (isHeadingLineStart(trimmed)) {
      // 兜底：行首像标题但无法拆分
      headingSeq += 1
      const label = outlineLabelForLine(trimmed) || trimmed.slice(0, 80)
      outline.push({
        kind: 'heading',
        page: currentPage,
        label,
        anchorId: `text-p${currentPage}-h${headingSeq}`,
      })
    }
  }
  return outline
}
