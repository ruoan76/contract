/**
 * AI 相关枚举标签
 */

export const AI_ENGINE_DIMENSION_LABELS: Record<string, string> = {
  compliance: '合规性',
  risk: '风险条款',
  financial: '财务条款',
  capability: '履约能力',
  anomaly: '异常检测',
  legal: '法律合规',
  compliance_check: '合规审查',
  risk_assessment: '风险条款',
  finance_check: '财务条款',
  performance_check: '履约能力',
  anomaly_detection: '异常检测',
  commercial: '商业条款',
  operational: '履约风险',
}

export const AI_DIMENSION_ORDER = [
  'compliance',
  'risk',
  'financial',
  'capability',
  'anomaly',
] as const

export const AI_REVIEW_STATUS_LABELS: Record<string, string> = {
  pending: '待审查',
  reviewing: '审查中',
  ai_done: 'AI 已完成',
  reviewed: '已复核',
  confirmed: '已确认',
  failed: '审查失败',
}

export const RISK_LEVEL_LABELS: Record<string, string> = {
  low: '低风险',
  medium: '中风险',
  high: '高风险',
  critical: '极高风险',
}

export const AI_ISSUE_HUMAN_STATUS_LABELS: Record<string, string> = {
  pending: '待确认',
  confirmed: '已确认',
  false_positive: '误报',
  dismissed: '已忽略',
}

export type ElementTagType = 'success' | 'warning' | 'danger' | 'info' | ''

export function riskLevelLabel(value?: string | null): string {
  if (!value) return '—'
  return RISK_LEVEL_LABELS[value] || value
}

export function riskLevelTagType(value?: string | null): ElementTagType {
  if (value === 'critical' || value === 'high') return 'danger'
  if (value === 'medium') return 'warning'
  if (value === 'low') return 'success'
  return 'info'
}

export function aiReviewStatusLabel(value?: string | null): string {
  if (!value) return '—'
  return AI_REVIEW_STATUS_LABELS[value] || value
}

export function aiDimensionLabel(value?: string | null): string {
  if (!value) return '—'
  return AI_ENGINE_DIMENSION_LABELS[value] || value
}

export function aiIssueHumanStatusLabel(value?: string | null): string {
  if (!value) return '—'
  return AI_ISSUE_HUMAN_STATUS_LABELS[value] || value
}

export function dimensionStatusTagType(status?: string | null): ElementTagType {
  if (status === 'failed') return 'danger'
  if (status === 'degraded') return 'warning'
  return ''
}
