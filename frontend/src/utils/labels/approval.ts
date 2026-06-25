/**
 * 审批相关枚举标签
 */

export const APPROVAL_NODE_LABELS: Record<string, string> = {
  dept_approval: '部门审批',
  legal_review: '法务审查',
  finance_review: '财务审查',
  executive_approval: '高管审批',
  board_approval: '董事会审批',
  done: '已完成',
}

export const FLOW_TYPE_LABELS: Record<string, string> = {
  simple: '简易流程',
  standard: '标准流程',
  special: '特殊流程',
  large_amount: '大额流程',
}

/** 审批配置 / 流程节点使用的角色 code（英文存库） */
export const APPROVER_ROLE_LABELS: Record<string, string> = {
  approver: '部门主管',
  legal: '法务专员',
  finance: '财务专员',
  executive: '高管',
}

export const APPROVER_ROLE_OPTIONS = Object.entries(APPROVER_ROLE_LABELS).map(([value, label]) => ({
  value,
  label,
}))

export function approverRoleLabel(code: string | undefined): string {
  if (!code) return '—'
  return APPROVER_ROLE_LABELS[code] || code
}

export const APPROVAL_FLOW_STATUS_LABELS: Record<string, string> = {
  approving: '审批中',
  approved: '已通过',
  rejected: '已驳回',
  returned: '已退回',
  pending: '待处理',
  completed: '已完成',
}

export function approvalFlowStatusLabel(value?: string | null): string {
  if (!value) return '—'
  return APPROVAL_FLOW_STATUS_LABELS[value] || value
}

export function approvalNodeLabel(value?: string | null): string {
  if (!value) return '—'
  return APPROVAL_NODE_LABELS[value] || value
}

export function flowTypeLabel(value?: string | null): string {
  if (!value) return '—'
  return FLOW_TYPE_LABELS[value] || value
}
