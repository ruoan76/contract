import { client } from './client'

export interface AiClauseReview {
  clause?: string
  dimension?: string
  risk_level?: string
  confidence?: number
  suggestion?: string
}

export interface AiReviewSummary {
  review_id?: string
  risk_level?: string
  risk_score?: number
  review_time?: string
  review_status?: string
  recommendation?: string
  summary?: Record<string, unknown>
  clause_reviews?: AiClauseReview[]
}

const DIMENSION_LABELS: Record<string, string> = {
  legal: '法律合规',
  financial: '财务风险',
  operational: '履约风险',
  compliance: '合规审查',
  commercial: '商业条款',
}

export function groupClausesByDimension(clauses: AiClauseReview[] = []) {
  const groups: Record<string, AiClauseReview[]> = {}
  for (const c of clauses) {
    const dim = c.dimension || 'legal'
    if (!groups[dim]) groups[dim] = []
    groups[dim].push(c)
  }
  return Object.entries(groups).map(([key, items]) => ({
    key,
    label: DIMENSION_LABELS[key] || key,
    items,
  }))
}

export interface AiReviewPollResult {
  review_id: string
  status: string
  message?: string
  overall?: {
    risk_level?: string
    risk_score?: number
    recommendation?: string
  }
  clauses?: AiClauseReview[]
}

export const aiReviewApi = {
  review: (contractId: number) =>
    client.post<{ review_id?: string; status?: string }>('/api/v1/ai-review/review', {
      contract_id: contractId,
    }),

  latest: (contractId: number) =>
    client.get<AiReviewSummary>(`/api/v1/ai-review/contracts/${contractId}/latest-review`),

  result: (reviewId: string) =>
    client.get<AiReviewPollResult>(`/api/v1/ai-review/${reviewId}/result`),

  feedback: (reviewId: string, type: 'false_positive' | 'false_negative', comment?: string) =>
    client.post<unknown>(`/api/v1/ai-review/${reviewId}/feedback`, { type, comment }),
}
