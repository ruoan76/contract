import type { AiReviewSummary } from '@/api/ai-review'
import type { AiSummaryPanelData, DimensionSummaryInput } from '@/utils/aiRecommendation'

/** 将 latest-review 映射为 AiSummaryPanel 所需结构（与 ReviewWorkspace 对齐） */
export function toSummaryPanelData(result: AiReviewSummary | null): AiSummaryPanelData | null {
  if (!result) return null
  const summary = result.summary as Record<string, unknown> | undefined
  const dimensionSummaries = summary?.dimensions as DimensionSummaryInput[] | undefined

  const topClauses = (result.clause_reviews || [])
    .filter((c) => c.risk_level === 'critical' || c.risk_level === 'high')
    .slice(0, 10)
    .map((c) => ({
      clause: c.clause,
      risk_level: c.risk_level,
      dimension: c.dimension,
      suggestion: c.suggestion,
    }))

  return {
    review_id: result.review_id,
    risk_level: result.risk_level,
    risk_score: result.risk_score,
    review_status: result.review_status,
    recommendation: result.recommendation,
    dimension_summaries: dimensionSummaries,
    top_clauses: topClauses,
  }
}
