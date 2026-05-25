import { client } from './client'

export interface AiClauseReview {
  clause?: string
  dimension?: string
  risk_level?: string
  confidence?: number
  suggestion?: string
  label_id?: string
  label_name?: string
  legal_basis?: string
  source?: 'rule' | 'llm' | string
  gate_id?: string
  revision_method?: string
  needs_research?: boolean
}

export interface AiReviewIssue {
  id?: number
  review_id?: string
  clause?: string
  clause_ref?: string
  dimension?: string
  label_id?: string
  label_name?: string
  gate_id?: string
  risk_level?: string
  confidence?: number
  title?: string
  description?: string
  suggestion?: string
  legal_basis?: string
  revision_method?: string
  source?: string
  needs_research?: boolean
  human_status?: string
  human_comment?: string
}

export interface AiGateItem {
  status?: string
  summary?: string
}

export interface AiRuleViolation {
  rule_id?: string
  rule_name?: string
  severity?: string
  message?: string
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
  rule_violations?: AiRuleViolation[]
  gates?: Record<string, AiGateItem>
}

/** 15 类风险标签（与 seeds risk_labels 对齐） */
export const LABEL_OPTIONS: { id: string; name: string }[] = [
  { id: 'RL-001', name: '付款条款' },
  { id: 'RL-002', name: '交付验收' },
  { id: 'RL-003', name: '违约责任' },
  { id: 'RL-004', name: '知识产权' },
  { id: 'RL-005', name: '保密义务' },
  { id: 'RL-006', name: '争议解决' },
  { id: 'RL-007', name: '不可抗力' },
  { id: 'RL-008', name: '合同期限' },
  { id: 'RL-009', name: '价格调整' },
  { id: 'RL-010', name: '质量保证' },
  { id: 'RL-011', name: '合规审查' },
  { id: 'RL-012', name: '主体资质' },
  { id: 'RL-013', name: '税务条款' },
  { id: 'RL-014', name: '数据安全' },
  { id: 'RL-015', name: '其他风险' },
]

const DIMENSION_LABELS: Record<string, string> = {
  legal: '法律合规',
  financial: '财务风险',
  operational: '履约风险',
  compliance: '合规审查',
  compliance_check: '合规审查',
  risk_assessment: '风险条款',
  finance_check: '财务条款',
  performance_check: '履约能力',
  anomaly_detection: '异常检测',
  commercial: '商业条款',
}

export function labelName(labelId?: string): string {
  if (!labelId) return '—'
  return LABEL_OPTIONS.find((l) => l.id === labelId)?.name || labelId
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

  listIssues: (reviewId: string, page = 1, pageSize = 50) =>
    client.get<{ items: AiReviewIssue[]; page: number; page_size: number }>(
      `/api/v1/ai-review/${reviewId}/issues`,
      { params: { page, page_size: pageSize } },
    ),

  patchIssue: (issueId: number, humanStatus: string, humanComment?: string) =>
    client.patch<{ id: number; human_status: string }>(`/api/v1/ai-review/issue/${issueId}`, {
      human_status: humanStatus,
      human_comment: humanComment,
    }),

  confirm: (reviewId: string) =>
    client.post<{ review_id: string; review_status: string }>(
      `/api/v1/ai-review/${reviewId}/confirm`,
      {},
    ),

  downloadReport: async (reviewId: string, format = 'pdf') => {
    const base = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
    const res = await fetch(`${base}/api/v1/ai-review/${reviewId}/report?format=${format}`)
    if (!res.ok) throw new Error('报告下载失败')
    return res.blob()
  },
}
