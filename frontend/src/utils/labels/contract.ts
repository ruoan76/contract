/**
 * 合同相关枚举标签
 */

export const CONTRACT_TYPE_LABELS: Record<string, string> = {
  purchase: '采购',
  sales: '销售',
  labor: '劳务',
  nda: '保密',
  cooperation: '合作',
  'legal-standard': '法务制式',
  service: '服务',
  other: '其他',
}

export const CONTRACT_STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  pending: '待审批',
  in_review: '评审中',
  reviewing: '审查中',
  returned: '已退回',
  approved: '已通过',
  seal_pending: '待用印',
  sealed: '已用印',
  signed: '已签署',
  executing: '执行中',
  archived: '已归档',
  rejected: '已拒绝',
  terminated: '已终止',
  void: '已作废',
  ai_screening: 'AI 初筛中',
  dept_approval: '部门主管审批',
  legal_review: '法务评审',
  finance_review: '财务评审',
  executive_approval: '高管审批',
  board_approval: '董事会审批',
  done: '流程结束',
}

export function contractTypeLabel(value?: string | null): string {
  if (!value) return '—'
  return CONTRACT_TYPE_LABELS[value] || value
}

export function contractStatusLabel(value?: string | null): string {
  if (!value) return '—'
  return CONTRACT_STATUS_LABELS[value] || (value || '—')
}
