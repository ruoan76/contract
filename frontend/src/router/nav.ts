export interface NavItem {
  name: string
  path: string
  title: string
  icon?: string
  group: string
}

/** 侧栏 17 项（对照 prototype ALL_NAV_PAGES） */
export const NAV_ITEMS: NavItem[] = [
  { name: 'dashboard', path: '/', title: '状态看板', icon: 'Odometer', group: '概览' },
  { name: 'messages', path: '/messages', title: '消息中心', icon: 'Bell', group: '概览' },
  { name: 'create', path: '/create', title: '新建合同', icon: 'EditPen', group: '起草' },
  { name: 'contracts', path: '/contracts', title: '合同列表', icon: 'Document', group: '起草' },
  { name: 'templates', path: '/templates', title: '模板管理', icon: 'Files', group: '起草' },
  { name: 'ai-review', path: '/ai-review', title: '审查报告', icon: 'MagicStick', group: 'AI审查' },
  { name: 'review-center', path: '/review-center', title: '评审中心', icon: 'View', group: '评审' },
  { name: 'review-workspace', path: '/review-workspace', title: '评审工作台', icon: 'Edit', group: '评审' },
  { name: 'review-history', path: '/review-history', title: '评审历史', icon: 'Clock', group: '评审' },
  { name: 'approvals', path: '/approvals', title: '待办审批', icon: 'Checked', group: '审批' },
  { name: 'seal', path: '/seal', title: '用印管理', icon: 'Stamp', group: '签署归档' },
  { name: 'archives', path: '/archives', title: '归档台账', icon: 'FolderOpened', group: '签署归档' },
  { name: 'counterparties', path: '/counterparties', title: '相对方管理', icon: 'OfficeBuilding', group: '基础数据' },
  { name: 'config', path: '/config', title: '审批配置', icon: 'Setting', group: '系统' },
  { name: 'users', path: '/users', title: '用户管理', icon: 'User', group: '系统' },
  { name: 'audit', path: '/audit', title: '审计日志', icon: 'List', group: '系统' },
]

export const ROUTE_TITLES: Record<string, [string, string]> = {
  dashboard: ['状态看板', '首页 / 状态看板'],
  messages: ['消息中心', '首页 / 消息中心'],
  create: ['新建合同', '起草 / 新建合同'],
  contracts: ['合同列表', '起草 / 合同列表'],
  templates: ['模板管理', '起草 / 模板管理'],
  'ai-review': ['审查报告', 'AI审查 / 审查报告'],
  'clause-compare': ['条款比对', '合同 / 条款比对'],
  'review-center': ['评审中心', '评审 / 评审中心'],
  'review-workspace': ['评审工作台', '评审 / 评审工作台'],
  'review-history': ['评审历史', '评审 / 评审历史'],
  approvals: ['待办审批', '审批 / 待办审批'],
  seal: ['用印管理', '签署归档 / 用印管理'],
  archives: ['归档台账', '签署归档 / 归档台账'],
  counterparties: ['相对方管理', '基础数据 / 相对方管理'],
  config: ['审批配置', '系统 / 审批配置'],
  users: ['用户管理', '系统 / 用户管理'],
  audit: ['审计日志', '系统 / 审计日志'],
  'contract-detail': ['合同详情', '合同 / 详情'],
  'approval-history': ['审批历史', '合同 / 审批历史'],
  'revision-workspace': ['修订工作台', '合同 / 修订'],
}
