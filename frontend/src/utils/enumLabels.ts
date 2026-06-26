/**
 * 后端枚举值 → 中文展示（与 docs/design/data-dictionary.md 对齐）
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

/** AI 五维审查引擎维度（英文 key → 中文） */
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
  unknown: '未知',
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

/** AI 审查五门禁 ID（与后端 report_pdf_theme 对齐） */
export const AI_GATE_LABELS: Record<string, string> = {
  gate_validity: '效力',
  gate_subject: '主体',
  gate_clause: '条款',
  gate_consistency: '一致性',
  gate_output: '输出',
}

/** 门禁卡片状态 */
export const GATE_STATUS_LABELS: Record<string, string> = {
  pass: '通过',
  fail: '未通过',
  warn: '需关注',
  pending: '待处理',
}

/** 维度分析状态（ok / degraded / failed） */
export const DIMENSION_ANALYSIS_STATUS_LABELS: Record<string, string> = {
  ok: '正常',
  degraded: '部分降级',
  failed: '分析失败',
}

/** 评审工作台角色 */
export const REVIEW_ROLE_LABELS: Record<string, string> = {
  legal: '法务',
  finance: '财务',
  executive: '高管',
}

/** 评审动作 */
export const REVIEW_ACTION_LABELS: Record<string, string> = {
  approve: '通过',
  reject: '驳回',
  return: '退回',
}

/** 清单矩阵结论 */
export const CHECKLIST_CONCLUSION_LABELS: Record<string, string> = {
  pass: '通过',
  fail: '未通过',
  attention: '需关注',
  unknown: '待确认',
}

export function gateIdLabel(value?: string | null): string {
  if (!value) return '—'
  return AI_GATE_LABELS[value] || value
}

export function gateStatusLabel(value?: string | null): string {
  if (!value) return '—'
  return GATE_STATUS_LABELS[value] || value
}

export function dimensionAnalysisStatusLabel(value?: string | null): string {
  if (!value) return '—'
  return DIMENSION_ANALYSIS_STATUS_LABELS[value] || value
}

export function reviewRoleLabel(value?: string | null): string {
  if (!value) return '—'
  return REVIEW_ROLE_LABELS[value] || value
}

export function reviewActionLabel(value?: string | null): string {
  if (!value) return '—'
  return REVIEW_ACTION_LABELS[value] || value
}

export function checklistConclusionLabel(value?: string | null): string {
  if (!value) return '—'
  return CHECKLIST_CONCLUSION_LABELS[value] || value
}

/** 审批历史节点动作 */
export const APPROVAL_STEP_ACTION_LABELS: Record<string, string> = {
  approve: '通过',
  reject: '驳回',
  return: '退回',
  pending: '待处理',
  delegate: '委托',
}

export function approvalStepActionLabel(value?: string | null): string {
  if (!value) return '—'
  return APPROVAL_STEP_ACTION_LABELS[value] || approvalFlowStatusLabel(value) || value
}

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

export const TEMPLATE_CATEGORY_LABELS: Record<string, string> = {
  ...CONTRACT_TYPE_LABELS,
  confidential: '保密',
}

export const APPROVAL_FLOW_STATUS_LABELS: Record<string, string> = {
  approving: '审批中',
  approved: '已通过',
  rejected: '已驳回',
  returned: '已退回',
  pending: '待处理',
  completed: '已完成',
}

/** 合同主状态 + 审批子状态（供 StatusTag 等复用） */
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

export const SEAL_STATUS_LABELS: Record<string, string> = {
  pending: '待确认',
  approved: '已确认',
  completed: '已完成',
  rejected: '已驳回',
}

export const SEAL_TYPE_LABELS: Record<string, string> = {
  公章: '公章',
  合同章: '合同章',
  财务章: '财务章',
  contract_seal: '合同章',
  official_seal: '公章',
  finance_seal: '财务章',
}

export const TEMPLATE_STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  pending_publish: '待发布',
  published: '已发布',
  deprecated: '已废止',
}

export const AUDIT_ACTION_LABELS: Record<string, string> = {
  submit_approval: '提交审批',
  approve_step: '审批通过',
  reject_step: '审批驳回',
  return_to_draft: '退回草稿',
  delegate_step: '审批委托',
  create_contract: '创建合同',
  update_contract: '更新合同',
  delete_contract: '删除合同',
}

export const AUDIT_RESOURCE_LABELS: Record<string, string> = {
  contract: '合同',
  approval: '审批',
  seal: '用印',
  user: '用户',
  template: '模板',
}

function lookup(map: Record<string, string>, value?: string | null, fallback = '—'): string {
  if (value == null || value === '') return fallback
  return map[value] ?? map[value.toLowerCase()] ?? value
}

export function flowTypeLabel(value?: string | null): string {
  return lookup(FLOW_TYPE_LABELS, value)
}

export function approvalNodeLabel(value?: string | null): string {
  return lookup(APPROVAL_NODE_LABELS, value)
}

export function contractTypeLabel(value?: string | null): string {
  return lookup(CONTRACT_TYPE_LABELS, value)
}

export function templateCategoryLabel(value?: string | null): string {
  return lookup(TEMPLATE_CATEGORY_LABELS, value)
}

export function approvalFlowStatusLabel(value?: string | null): string {
  return lookup(APPROVAL_FLOW_STATUS_LABELS, value)
}

export function contractStatusLabel(value?: string | null): string {
  return lookup(CONTRACT_STATUS_LABELS, value, value || '—')
}

export function sealStatusLabel(value?: string | null): string {
  return lookup(SEAL_STATUS_LABELS, value)
}

export function sealTypeLabel(value?: string | null): string {
  return lookup(SEAL_TYPE_LABELS, value)
}

export function templateStatusLabel(value?: string | null): string {
  return lookup(TEMPLATE_STATUS_LABELS, value)
}

export function auditActionLabel(value?: string | null): string {
  return lookup(AUDIT_ACTION_LABELS, value, value || '—')
}

export function auditResourceLabel(value?: string | null): string {
  return lookup(AUDIT_RESOURCE_LABELS, value, value || '—')
}
