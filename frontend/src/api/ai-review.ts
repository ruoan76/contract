import { client } from './client'

export interface AiReviewSummary {
  review_id?: string
  risk_level?: string
  risk_score?: number
  review_time?: string
  review_status?: string
  clause_reviews?: Array<{
    clause?: string
    risk_level?: string
    confidence?: number
    suggestion?: string
  }>
}

export const aiReviewApi = {
  review: (contractId: number) =>
    client.post<{ review_id?: string }>('/api/v1/ai-review/review', { contract_id: contractId }),

  latest: (contractId: number) =>
    client.get<AiReviewSummary>(`/api/v1/ai-review/contracts/${contractId}/latest-review`),

  feedback: (reviewId: string, type: 'false_positive' | 'false_negative', comment?: string) =>
    client.post<unknown>(`/api/v1/ai-review/${reviewId}/feedback`, { type, comment }),
}
