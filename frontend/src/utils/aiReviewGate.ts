import type { AiGateItem, AiReviewSummary } from '@/api/ai-review'
import type { AppRole } from '@/types/models'
import { aiDimensionLabel } from '@/utils/enumLabels'

const AI_READY = new Set(['ai_done', 'reviewed', 'confirmed'])
const LEGAL_ROLES = new Set<AppRole>(['legal', 'admin'])

export interface PrimaryActionSpec {
  label: string
  action: 'runReview' | 'confirmReport' | 'submitLegalReview' | 'goReviewWorkspace' | 'none'
  disabled: boolean
  disabledReason?: string
  loading?: boolean
}

export interface StatusBarSpec {
  type: 'info' | 'warning' | 'error'
  title: string
  description?: string
}

/** 与 ReviewWorkspace aiGateReady 对齐 */
export function isAiReviewReady(result: AiReviewSummary | null | undefined): boolean {
  if (!result?.review_status) return false
  if (!AI_READY.has(result.review_status)) return false
  if (result.gates?.gate_validity?.status === 'fail') return false
  return true
}

export function getAiGateBlockReason(result: AiReviewSummary | null | undefined): string | null {
  if (!result) return '请先完成 AI 审查'
  const st = result.review_status
  if (!st) return '请先完成 AI 审查'
  if (st === 'reviewing' || st === 'pending') return 'AI 审查进行中，请稍后再操作'
  if (st === 'failed') return null
  if (!AI_READY.has(st)) return '请先完成 AI 审查后再提交评审'
  if (result.gates?.gate_validity?.status === 'fail') {
    return '效力门禁未通过，请先处理效力相关问题'
  }
  const completeness =
    result.review_completeness ||
    (result.summary as { review_completeness?: string } | undefined)?.review_completeness
  if (completeness === 'partial') {
    return '审查未完整完成，结论仅供参考，请法务重点复核后再提交'
  }
  return null
}

export function buildStatusBar(
  result: AiReviewSummary | null | undefined,
  options: {
    isReviewing: boolean
    polling: boolean
    failedDimensions: string[]
    truncationHint?: string
  },
): StatusBarSpec | null {
  if (options.isReviewing || options.polling) {
    return {
      type: 'info',
      title: 'AI 审查进行中',
      description: '正在分析合同条款，完成后将自动刷新报告（约 1–3 分钟）。',
    }
  }
  if (result?.review_status === 'failed') {
    return {
      type: 'error',
      title: 'AI 审查失败',
      description: 'AI 推理服务未就绪或分析异常，请稍后重新审查或联系管理员。',
    }
  }
  const completeness =
    result?.review_completeness ||
    (result?.summary as { review_completeness?: string } | undefined)?.review_completeness
  if (completeness && completeness !== 'full') {
    const failedNames = options.failedDimensions.map((d) => aiDimensionLabel(d)).join('、')
    const failedPart = failedNames ? `未成功维度：${failedNames}。` : ''
    if (completeness === 'failed') {
      return {
        type: 'error',
        title: 'AI 审查失败',
        description: `请稍后重试或联系管理员，暂勿仅依据风险分决策。${failedPart}`,
      }
    }
    return {
      type: 'warning',
      title: '审查未完整完成',
      description: `部分维度未成功分析，结论仅供参考，请法务重点复核。${failedPart}`,
    }
  }
  if (options.truncationHint) {
    return {
      type: 'info',
      title: options.truncationHint,
    }
  }
  return null
}

export function buildPrimaryAction(
  result: AiReviewSummary | null | undefined,
  role: AppRole,
  options: { isReviewing: boolean; polling: boolean; hasContract: boolean },
): PrimaryActionSpec {
  if (!options.hasContract) {
    return { label: '触发审查', action: 'none', disabled: true }
  }
  if (options.isReviewing || options.polling) {
    return { label: '审查中…', action: 'none', disabled: true, loading: true }
  }
  if (!result) {
    return { label: '触发审查', action: 'runReview', disabled: false }
  }
  if (result.review_status === 'failed') {
    return { label: '重新审查', action: 'runReview', disabled: false }
  }
  if (result.review_status === 'ai_done') {
    const block = getAiGateBlockReason(result)
    const isLegal = LEGAL_ROLES.has(role)
    return {
      label: isLegal ? '确认 AI 报告' : '提交法务评审',
      action: isLegal ? 'confirmReport' : 'submitLegalReview',
      disabled: Boolean(block),
      disabledReason: block || undefined,
    }
  }
  if (result.review_status === 'reviewed' || result.review_status === 'confirmed') {
    return { label: '进入评审工作台', action: 'goReviewWorkspace', disabled: false }
  }
  return { label: '触发审查', action: 'runReview', disabled: false }
}

/** 门禁点击钻取：预填条款明细 Tab 筛选 */
export const GATE_DRILL_FILTERS: Record<
  string,
  { riskLevel?: string; gateId?: string }
> = {
  gate_validity: { gateId: 'gate_validity' },
  gate_subject: { gateId: 'gate_subject' },
  gate_clause: { riskLevel: 'high' },
  gate_consistency: { riskLevel: 'medium', gateId: 'gate_consistency' },
  gate_output: { riskLevel: 'low' },
}

export const GATE_ORDER = [
  'gate_validity',
  'gate_subject',
  'gate_clause',
  'gate_consistency',
  'gate_output',
] as const

export function orderedGates(
  gates: Record<string, AiGateItem> | undefined,
): Array<[string, AiGateItem]> {
  if (!gates) return []
  const entries = Object.entries(gates)
  return GATE_ORDER.map((key) => {
    const item = gates[key]
    return item ? ([key, item] as [string, AiGateItem]) : null
  }).filter(Boolean) as Array<[string, AiGateItem]>
}
