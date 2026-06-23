import {
  AI_DIMENSION_ORDER,
  AI_ENGINE_DIMENSION_LABELS,
  aiDimensionLabel,
} from './enumLabels'

export interface DimensionBlock {
  key: string
  label: string
  content: string
  score?: number
  status?: string
}

export interface DimensionSummaryInput {
  dimension?: string
  score?: number
  summary?: string
  status?: string
}

export interface AiSummaryPanelData {
  review_id?: string
  risk_level?: string
  risk_score?: number
  review_status?: string
  recommendation?: string
  dimension_summaries?: DimensionSummaryInput[]
  top_clauses?: Array<{
    clause?: string
    risk_level?: string
    dimension?: string
    suggestion?: string
  }>
}

const BRACKET_PATTERN = /【(\w+)】/g

/**
 * 解析 recommendation 中 【compliance】…【risk】… 格式的五维摘要
 */
export function parseRecommendation(text: string | undefined | null): DimensionBlock[] {
  if (!text?.trim()) return []

  const matches = [...text.matchAll(BRACKET_PATTERN)]
  if (matches.length === 0) {
    return [{ key: 'overall', label: '总体建议', content: text.trim() }]
  }

  const blocks: DimensionBlock[] = []
  for (let i = 0; i < matches.length; i++) {
    const m = matches[i]
    const key = m[1]
    const start = (m.index ?? 0) + m[0].length
    const end = i + 1 < matches.length ? (matches[i + 1].index ?? text.length) : text.length
    const content = text.slice(start, end).trim()
    if (content) {
      blocks.push({
        key,
        label: aiDimensionLabel(key),
        content,
      })
    }
  }
  return sortDimensionBlocks(blocks)
}

export function dimensionSummariesToBlocks(
  summaries: DimensionSummaryInput[] | undefined | null,
): DimensionBlock[] {
  if (!summaries?.length) return []
  const blocks = summaries
    .filter((d) => d.summary?.trim() || d.dimension)
    .map((d) => ({
      key: d.dimension || 'unknown',
      label: aiDimensionLabel(d.dimension),
      content: (d.summary || '').trim(),
      score: d.score,
      status: d.status,
    }))
  return sortDimensionBlocks(blocks)
}

export function buildDimensionBlocks(options: {
  dimensionSummaries?: DimensionSummaryInput[] | null
  recommendation?: string | null
}): DimensionBlock[] {
  const fromApi = dimensionSummariesToBlocks(options.dimensionSummaries)
  if (fromApi.length) return fromApi
  return parseRecommendation(options.recommendation)
}

function sortDimensionBlocks(blocks: DimensionBlock[]): DimensionBlock[] {
  const orderIndex = new Map(AI_DIMENSION_ORDER.map((k, i) => [k, i]))
  return [...blocks].sort((a, b) => {
    const ia = orderIndex.get(a.key as (typeof AI_DIMENSION_ORDER)[number]) ?? 99
    const ib = orderIndex.get(b.key as (typeof AI_DIMENSION_ORDER)[number]) ?? 99
    if (ia !== ib) return ia - ib
    return a.key.localeCompare(b.key)
  })
}

export { AI_ENGINE_DIMENSION_LABELS }
