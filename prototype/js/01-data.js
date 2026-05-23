/**
 * 样例合同与角色配置。
 * visiblePages 须与 docs/design/permission-matrix.md §3、DESIGN_STATUS §3.4 一致；
 * 变更后同步 prototype/_test-lib.mjs 中 ROLE_VISIBLE。
 */
/** 默认样例数据 */
const defaultContracts = [
  { no: 'DEMO-01', name: '小额办公耗材采购', type: 'purchase', typeName: '采购', counterparty: '得力集团', amount: 80000, status: 'pending', statusName: '待审批', approvalStatus: '部门主管审批中', risk: 'low', riskName: '低风险', creator: '李四', time: '2024-03-01 09:00', flowType: 'simple' },
  { no: 'DEMO-03', name: '核心机房建设合同', type: 'purchase', typeName: '采购', counterparty: '华为技术', amount: 2500000, status: 'pending', statusName: '待审批', approvalStatus: '董事会审批中', risk: 'high', riskName: '高风险', creator: '孙七', time: '2024-03-02 14:00', flowType: 'special' },
  { no: 'DEMO-05', name: '软件开发服务合同', type: 'purchase', typeName: '采购', counterparty: '中科软', amount: 320000, status: 'pending', statusName: '待审批', approvalStatus: '法务审核中', risk: 'medium', riskName: '中风险', creator: '王五', time: '2024-03-03 10:00', flowType: 'standard' },
  { no: 'CTR-20240115-0001', name: '服务器采购合同', type: 'purchase', typeName: '采购', counterparty: '华为技术', amount: 2500000, status: 'approved', statusName: '已通过', approvalStatus: '已通过', risk: 'medium', riskName: '中风险', creator: '张三', time: '2024-01-15 09:00' },
  { no: 'CTR-20240115-0002', name: '网络设备采购合同', type: 'purchase', typeName: '采购', counterparty: '新华三', amount: 850000, status: 'pending', statusName: '待审批', approvalStatus: '部门主管审批中', risk: 'low', riskName: '低风险', creator: '李四', time: '2024-01-15 10:30' },
  { no: 'CTR-20240114-0003', name: '云服务年框协议', type: 'purchase', typeName: '采购', counterparty: '阿里云', amount: 800000, status: 'approved', statusName: '已通过', approvalStatus: '已通过', risk: 'low', riskName: '低风险', creator: '王五', time: '2024-01-14 14:20' },
  { no: 'CTR-20240114-0004', name: '年度 IT 运维服务合同', type: 'purchase', typeName: '采购', counterparty: '中科软', amount: 320000, status: 'pending', statusName: '待审批', approvalStatus: '法务审核中', risk: 'low', riskName: '低风险', creator: '王五', time: '2024-01-14 16:20' },
  { no: 'CTR-20240113-0005', name: '办公区装修合同', type: 'purchase', typeName: '采购', counterparty: '中建装饰', amount: 1200000, status: 'approved', statusName: '已通过', approvalStatus: '已通过', risk: 'high', riskName: '高风险', creator: '赵六', time: '2024-01-13 11:00' },
  { no: 'CTR-20240113-0006', name: '软件授权许可协议', type: 'other', typeName: '其他', counterparty: '微软中国', amount: 150000, status: 'pending', statusName: '待审批', approvalStatus: '财务审核中', risk: 'low', riskName: '低风险', creator: '赵六', time: '2024-01-13 09:15' },
  { no: 'CTR-20240112-0007', name: '数据中心租赁合同', type: 'purchase', typeName: '采购', counterparty: '万国数据', amount: 2400000, status: 'pending', statusName: '待审批', approvalStatus: '高管审批中', risk: 'medium', riskName: '中风险', creator: '孙七', time: '2024-01-12 14:00' },
  { no: 'CTR-20240111-0008', name: '产品代理销售合同', type: 'sales', typeName: '销售', counterparty: '神州数码', amount: 3500000, status: 'signed', statusName: '已签署', approvalStatus: '待归档', risk: 'low', riskName: '低风险', creator: '周八', time: '2024-01-11 10:00' },
  { no: 'CTR-20240111-0009', name: '员工体检服务合同', type: 'labor', typeName: '劳务', counterparty: '美年健康', amount: 85000, status: 'pending', statusName: '待审批', approvalStatus: '部门主管审批中', risk: 'low', riskName: '低风险', creator: '周八', time: '2024-01-11 11:30' },
  { no: 'CTR-20240110-0010', name: '保密协议（NDA）', type: 'nda', typeName: '保密', counterparty: '腾讯科技', amount: 0, status: 'archived', statusName: '已归档', approvalStatus: '已归档', risk: 'low', riskName: '低风险', creator: '吴九', time: '2024-01-10 15:00' },
  { no: 'CTR-20240108-0011', name: '年度安保合同', type: 'labor', typeName: '劳务', counterparty: '中安保', amount: 360000, status: 'executing', statusName: '执行中', approvalStatus: '履约中', risk: 'low', riskName: '低风险', creator: '张三', time: '2024-01-08 09:00', startDate: '2023-06-01', endDate: '2024-02-10' },
  { no: 'CTR-20231201-0012', name: '物流合作协议', type: 'purchase', typeName: '采购', counterparty: '顺丰速运', amount: 650000, status: 'terminated', statusName: '已终止', approvalStatus: '已终止', risk: 'medium', riskName: '中风险', creator: '赵六', time: '2023-12-01 14:00', endDate: '2024-12-31' },
  { no: 'CTR-20240201-0013', name: '办公用品年度采购', type: 'purchase', typeName: '采购', counterparty: '得力集团', amount: 280000, status: 'executing', statusName: '执行中', approvalStatus: '正常履约', risk: 'low', riskName: '低风险', creator: '李四', time: '2024-02-01 10:00', endDate: '2025-08-15' },
  { no: 'CTR-20240120-0014', name: 'IT 设备维保合同', type: 'purchase', typeName: '采购', counterparty: '联想集团', amount: 1200000, status: 'executing', statusName: '执行中', approvalStatus: '正常履约', risk: 'low', riskName: '低风险', creator: '王五', time: '2024-01-20 08:30', endDate: '2025-01-30' },
];

/** 金额阈值 → 流程类型（与 page-config、workflow-vs-review 一致；可被 localStorage.flow_thresholds 覆盖） */
const DEFAULT_FLOW_THRESHOLDS = {
  purchase: { simpleMax: 100000, standardMax: 1000000 },
  sales: { simpleMax: 500000, standardMax: Infinity },
};

function resolveFlowType(contractType, amountNum) {
  let thresholds = DEFAULT_FLOW_THRESHOLDS;
  try {
    const stored = localStorage.getItem('flow_thresholds');
    if (stored) thresholds = { ...thresholds, ...JSON.parse(stored) };
  } catch (e) {
    /* 忽略损坏的本地配置 */
  }
  const n = Number(amountNum) || 0;
  if (contractType === 'labor' || contractType === 'nda') return 'standard';
  if (contractType === 'sales') {
    const t = thresholds.sales || DEFAULT_FLOW_THRESHOLDS.sales;
    return n > (t.simpleMax ?? 500000) ? 'standard' : 'simple';
  }
  const t = thresholds.purchase || DEFAULT_FLOW_THRESHOLDS.purchase;
  if (n > (t.standardMax ?? 1000000)) return 'special';
  if (n > (t.simpleMax ?? 100000)) return 'standard';
  return 'simple';
}

/** 侧栏全部菜单页（原型始终展示；正式环境按各角色 visiblePages 控制） */
const ALL_NAV_PAGES = [
  'dashboard', 'messages', 'create', 'contracts', 'templates',
  'ai-review', 'clause-compare', 'review-center', 'review-workspace', 'review-history',
  'approvals', 'seal', 'archives', 'counterparties', 'config', 'users', 'audit',
];

/**
 * 正式环境各角色可见侧栏（见 docs/design/permission-matrix.md）
 * 原型不隐藏菜单，仅对无权限项加 nav-restricted 样式
 */
const roleConfig = {
  drafter: { name: '张三', dept: '采购部', title: '业务员', visiblePages: ['dashboard', 'messages', 'contracts', 'create', 'templates', 'ai-review', 'archives', 'counterparties', 'revision-workspace'] },
  approver: { name: '张三', dept: '采购部', title: '部门主管', visiblePages: ['dashboard', 'messages', 'contracts', 'create', 'templates', 'ai-review', 'clause-compare', 'approvals', 'archives', 'review-center', 'review-workspace', 'counterparties', 'config'] },
  legal: { name: '刘法务', dept: '法务部', title: '法务专员', visiblePages: ['dashboard', 'contracts', 'ai-review', 'clause-compare', 'seal', 'archives', 'review-center', 'review-workspace', 'templates'] },
  finance: { name: '王财务', dept: '财务部', title: '财务专员', visiblePages: ['dashboard', 'contracts', 'ai-review', 'clause-compare', 'archives', 'review-center', 'review-workspace'] },
  archivist: { name: '陈档案', dept: '综合部', title: '档案管理员', visiblePages: ['dashboard', 'contracts', 'seal', 'archives'] },
  admin: { name: '管理员', dept: '信息部', title: '系统管理员', visiblePages: ALL_NAV_PAGES.slice() },
};
