// ====== 全局变量（由 99-init.js 赋值） ======
var state;
var contracts;
var workspaceConfirmed;

// 渲染合同列表
function renderContracts(data) {
  const tbody = document.getElementById('contract-table-body');
  const statusMap = { draft: 'tag-blue', pending: 'tag-yellow', approved: 'tag-green', signed: 'tag-green', executing: 'tag-green', terminated: 'tag-red', archived: 'tag-gray' };
  const riskMap = { high: 'tag-red', medium: 'tag-yellow', low: 'tag-green' };
  
  const { pageData } = getPageData(data, contractPage, contractPageSize);
  
  tbody.innerHTML = pageData.map(c => `
    <tr>
      <td><code>${c.no}</code></td>
      <td style="font-weight:500">${c.name}</td>
      <td><span class="tag tag-blue">${c.typeName}</span></td>
      <td>${c.counterparty}</td>
      <td style="font-weight:600">${c.amount > 0 ? '¥ ' + c.amount.toLocaleString() : '-'}</td>
      <td><span class="tag ${statusMap[c.status]}">${c.statusName}</span></td>
      <td style="font-size:12px;color:var(--gray-600)">${c.approvalStatus}</td>
      <td><span class="tag ${riskMap[c.risk]}">${c.riskName}</span></td>
      <td>${c.creator}</td>
      <td>${c.time}</td>
      <td>
        <button class="btn btn-outline btn-sm" onclick="showContractDetail('${c.no}')">查看</button>
        ${c.status !== 'draft' ? '<button class="btn btn-outline btn-sm" onclick="showApprovalHistory(\'' + c.no + '\')">审批历史</button>' : ''}
        ${c.status === 'pending' ? '<button class="btn btn-primary btn-sm" onclick="switchPage(\'approvals\')">审批</button>' : ''}
        ${c.status === 'draft' ? '<button class="btn btn-outline btn-sm" onclick="editDraftContract(\'' + c.no + '\')">编辑</button><button class="btn btn-danger btn-sm" onclick="event.stopPropagation();deleteContract(\'' + c.no + '\')">删除</button>' : ''}${c.status === 'archived' || c.status === 'terminated' ? '<button class="btn btn-outline btn-sm" onclick="event.stopPropagation();voidContract(\'' + c.no + '\')">作废</button>' : ''}
      </td>
    </tr>
  `).join('');
  
  document.getElementById('contract-count').textContent = `(共 ${data.length} 份)`;
  // 渲染分页
  const { totalPages } = getPageData(data, contractPage, contractPageSize);
  renderPagination('contract-pagination', contractPage, totalPages, 'changeContractPage');
}

// 分页
let contractPage = 1;
const contractPageSize = 5;

function getPageData(data, page, size) {
  const start = (page - 1) * size;
  return { pageData: data.slice(start, start + size), totalPages: Math.ceil(data.length / size) };
}

function renderPagination(containerId, page, totalPages, onPageChange) {
  const container = document.getElementById(containerId);
  if (!container || totalPages <= 1) { if (container) container.innerHTML = ''; return; }
  let html = `<button ${page === 1 ? 'disabled' : ''} onclick="event.stopPropagation();(${onPageChange})(${page - 1})">◀</button>`;
  for (let i = 1; i <= totalPages; i++) {
    html += `<button class="${i === page ? 'active' : ''}" onclick="event.stopPropagation();(${onPageChange})(${i})">${i}</button>`;
  }
  html += `<button ${page === totalPages ? 'disabled' : ''} onclick="event.stopPropagation();(${onPageChange})(${page + 1})">▶</button>`;
  html += `<span style="margin-left:8px;font-size:12px;color:var(--gray-500)">第 ${page}/${totalPages} 页</span>`;
  container.innerHTML = html;
}

function changeContractPage(page) {
  contractPage = page;
  renderContracts(contracts);
}

// 到期预警计算
function calcDaysRemaining(endDateStr) {
  if (!endDateStr) return null;
  const end = new Date(endDateStr);
  const today = new Date();
  const diff = Math.ceil((end - today) / (1000 * 60 * 60 * 24));
  return diff;
}

function getExpiryStatus(diff) {
  if (diff === null) return null;
  if (diff < 0) return { label: '已逾期 ' + Math.abs(diff) + ' 天', cls: 'tag-red', severity: 'overdue' };
  if (diff <= 7) return { label: '剩余 ' + diff + ' 天', cls: 'tag-red', severity: 'critical' };
  if (diff <= 15) return { label: '剩余 ' + diff + ' 天', cls: 'tag-yellow', severity: 'warning' };
  if (diff <= 30) return { label: '剩余 ' + diff + ' 天', cls: 'tag-yellow', severity: 'info' };
  return null; // normal, no warning needed
}

function getExpiringContracts() {
  return contracts.filter(c => {
    if (c.status === 'terminated' || c.status === 'archived') return false;
    const diff = calcDaysRemaining(c.endDate);
    return diff !== null && diff <= 30;
  });
}

function getOverdueContracts() {
  return contracts.filter(c => {
    if (c.status === 'terminated' || c.status === 'archived') return false;
    const diff = calcDaysRemaining(c.endDate);
    return diff !== null && diff < 0;
  });
}

// 删除/作废合同
function deleteContract(no) {
  if (!confirm('确定删除该合同？此操作不可撤销。')) return;
  contracts = contracts.filter(c => c.no !== no);
  persistState();
  renderContracts(contracts);
  showToast('合同已删除');
}

function voidContract(no) {
  if (!confirm('确定作废该合同？')) return;
  const c = contracts.find(c => c.no === no);
  if (c) {
    c.status = 'terminated';
    c.statusName = '已终止';
    c.approvalStatus = '已作废';
  }
  persistState();
  renderContracts(contracts);
  showToast('合同已作废');
}

function filterUsers() { showToast('已按条件筛选用户列表'); }

function filterContracts() {
  contractPage = 1;
  const search = document.getElementById('contract-search').value.toLowerCase();
  const type = document.getElementById('contract-type-filter').value;
  const status = document.getElementById('contract-status-filter').value;
  const risk = document.getElementById('contract-risk-filter').value;
  
  let filtered = contracts.filter(c => {
    if (search && !c.no.toLowerCase().includes(search) && !c.name.toLowerCase().includes(search)) return false;
    if (type && c.type !== type) return false;
    if (status && c.status !== status) return false;
    if (risk && c.risk !== risk) return false;
    return true;
  });
  
  renderContracts(filtered);
}

function resetFilters() {
  contractPage = 1;
  document.getElementById('contract-search').value = '';
  document.getElementById('contract-type-filter').value = '';
  document.getElementById('contract-status-filter').value = '';
  document.getElementById('contract-risk-filter').value = '';
  renderContracts(contracts);
}

/** 下钻页不受侧栏 RBAC 限制 */
const DRILLDOWN_PAGES = ['contract-detail', 'approval-history', 'revision-workspace'];

function canAccessPage(pageId) {
  if (!state?.strictRbac) return true;
  if (DRILLDOWN_PAGES.includes(pageId)) return true;
  if (typeof ALL_NAV_PAGES !== 'undefined' && !ALL_NAV_PAGES.includes(pageId)) return true;
  const role = state.role || 'approver';
  const visible = roleConfig[role]?.visiblePages || [];
  return visible.includes(pageId);
}

function toggleStrictRbacMode(enabled) {
  state.strictRbac = !!enabled;
  persistState();
  const role = state.role || document.getElementById('role-select')?.value || 'approver';
  switchRole(role);
  showToast(enabled ? '已开启严格权限：无权限菜单已隐藏' : '已关闭严格权限：展示全部菜单（无权限项半透明）');
}

function goArchivesExpiring() {
  switchPage('archives');
  setTimeout(() => {
    if (typeof filterContractsByDate === 'function') filterContractsByDate('expiring');
  }, 200);
}

// 页面切换
function switchPage(pageId) {
  if (!canAccessPage(pageId)) {
    showToast('⚠️ 当前角色无权访问「' + pageId + '」');
    return;
  }
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  
  const page = document.getElementById('page-' + pageId);
  if (page) page.classList.add('active');
  
  // 高亮导航
  const navItems = document.querySelectorAll('.nav-item');
  const pageMap = {
    'dashboard': 0, 'messages': 1, 'create': 2, 'contracts': 3,
    'templates': 4, 'ai-review': 5, 'clause-compare': 6, 'review-center': 7,
    'review-workspace': 8, 'review-history': 9, 'approvals': 10,
    'seal': 11, 'archives': 12,
    'counterparties': 13, 'config': 14, 'users': 15, 'audit': 16,
    'contract-detail': -1, 'revision-workspace': -1, 'approval-history': -1
  };
  const navIdx = pageMap[pageId];
  if (navIdx !== undefined && navIdx >= 0 && navItems[navIdx]) {
    navItems[navIdx].classList.add('active');
  }
  
  // 更新标题
const titles = {
    'dashboard': ['状态看板', '概览 / 状态看板'],
    'messages': ['消息中心', '概览 / 消息中心'],
    'create': ['新建合同', '起草 / 新建合同'],
    'contracts': ['合同列表', '起草 / 合同列表'],
    'templates': ['模板管理', '起草 / 模板管理'],
    'ai-review': ['审查报告', 'AI审查 / 审查报告'],
    'clause-compare': ['条款比对', 'AI审查 / 条款比对'],
    'review-center': ['评审中心', '评审 / 评审中心'],
    'review-workspace': ['评审工作台', '评审 / 评审工作台'],
    'review-history': ['评审历史', '评审 / 评审历史'],
    'approvals': ['待办审批', '审批 / 待办审批'],
    'approval-history': ['审批历史', '合同 / 审批历史'],
    'seal': ['用印管理', '签署归档 / 用印管理'],
    'archives': ['归档台账', '签署归档 / 归档台账'],
    'counterparties': ['相对方管理', '基础数据 / 相对方管理'],
    'config': ['审批配置', '系统 / 审批配置'],
    'users': ['用户管理', '系统 / 用户管理'],
    'audit': ['审计日志', '系统 / 审计日志'],
    'contract-detail': ['合同详情', '起草 / 合同详情'],
    'revision-workspace': ['修订工作台', '起草 / 修订工作台']
  };
  
  if (titles[pageId]) {
    document.getElementById('page-title').textContent = titles[pageId][0];
    document.getElementById('page-breadcrumb').textContent = titles[pageId][1];
  }
  
  // 初始化合同列表
  if (pageId === 'contracts') renderContracts(contracts);
  if (pageId === 'review-workspace') {
    const ft = sessionStorage.getItem('current_contract_flow') || 'standard';
    applyWorkspaceFlowTabs(ft);
  }
  if (pageId === 'dashboard') updateDashboardStats();
  if (pageId === 'approval-history') {
    const no = sessionStorage.getItem('approval_history_contract');
    if (no) {
      const c = contracts.find((x) => x.no === no);
      if (c) renderApprovalHistory(c);
    }
  }
  if (pageId === 'create') {
    const draft = loadDraft();
    if (draft && draft.title) {
      document.getElementById('btn-restore-draft').style.display = 'inline-flex';
      document.getElementById('btn-clear-draft').style.display = 'inline-flex';
      document.getElementById('draft-badge').style.display = 'inline-flex';
      document.getElementById('draft-badge').innerHTML = '<span class="tag tag-yellow" style="font-size:10px">💾 草稿 (' + draft.savedAt + ')</span>';
      startDraftAutoSave();
    }
  }
  if (pageId === 'ai-review' && typeof initAiReviewLabelFilter === 'function') {
    initAiReviewLabelFilter();
  }
  if (pageId === 'ai-review' || pageId === 'contract-detail' || pageId === 'review-workspace') {
    renderContractContext(getActiveContract());
  }
  if (pageId === 'audit' && typeof renderAuditLog === 'function') {
    renderAuditLog();
  }
}

// 模态框（合同详情统一走下钻页，不再使用弹窗）
function showModal(id) {
  if (id === 'contract-detail') {
    const no =
      sessionStorage.getItem('current_contract_no') ||
      getActiveContract()?.no ||
      'CTR-20240115-0001';
    showContractDetail(no);
    return;
  }
  const el = document.getElementById('modal-' + id);
  if (el) el.classList.add('show');
}
function hideModal(id) {
  if (id === 'contract-detail') return;
  const el = document.getElementById('modal-' + id);
  if (el) el.classList.remove('show');
}

/** 从合同详情进入 AI 审查（携带当前合同上下文） */
function openAiReviewFromDetail() {
  const c = getActiveContract();
  if (c?.no) sessionStorage.setItem('current_contract_no', c.no);
  if (c?.flowType) sessionStorage.setItem('current_contract_flow', c.flowType);
  switchPage('ai-review');
  renderContractContext(c);
}

/** 从合同详情进入评审工作台 */
function openReviewWorkspaceFromDetail() {
  const c = getActiveContract();
  if (c?.no) openReviewWorkspace(c.no);
}

// ====== 合同上下文（P0-03） ======
function getActiveContract() {
  const no = sessionStorage.getItem('current_contract_no');
  if (no) {
    const found = contracts.find((x) => x.no === no);
    if (found) return found;
  }
  return contracts.find((c) => c.no === 'CTR-20240115-0001') || contracts[0];
}

function formatContractAmount(amount) {
  if (amount == null || amount === '') return '—';
  const n = Number(amount);
  if (Number.isNaN(n)) return String(amount);
  return '¥ ' + n.toLocaleString('zh-CN');
}

function riskTagClass(risk) {
  if (risk === 'high') return 'tag tag-red';
  if (risk === 'medium') return 'tag tag-yellow';
  return 'tag tag-green';
}

function renderContractContext(contract) {
  if (!contract) return;
  const title = contract.no + ' ' + (contract.name || contract.title || '');
  const flowNames = { simple: '简易流程', standard: '标准流程', special: '特殊流程' };
  const flowName = contract.flowTypeName || flowNames[contract.flowType] || '标准流程';
  const typeName = contract.typeName || contract.type || '—';
  const riskName = contract.riskName || '—';

  const titleEl = document.getElementById('detail-contract-title');
  if (titleEl) titleEl.textContent = title;

  const tagsEl = document.getElementById('detail-status-tags');
  if (tagsEl) {
    tagsEl.innerHTML =
      '<span class="tag tag-green">' + (contract.statusName || contract.status || '—') + '</span>' +
      '<span class="' + riskTagClass(contract.risk) + '">' + riskName + '</span>';
  }

  const setField = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };
  setField('detail-field-type', typeName);
  setField('detail-field-amount', formatContractAmount(contract.amount));
  setField('detail-field-counterparty', contract.counterparty || '—');
  setField('detail-field-start', contract.startDate || '—');
  setField('detail-field-end', contract.endDate || '—');
  setField('detail-field-creator', (contract.creator || '—') + (contract.time ? ' · ' + contract.time : ''));

  const aiTitle = document.getElementById('ai-review-title');
  if (aiTitle) aiTitle.textContent = 'AI审查报告 - ' + title;

  const flowTag = document.getElementById('ai-review-flow-tag');
  if (flowTag) {
    flowTag.textContent = flowName;
    flowTag.className = 'tag tag-yellow';
    if (contract.flowType === 'simple') flowTag.className = 'tag tag-green';
    if (contract.flowType === 'special') flowTag.className = 'tag tag-red';
  }

  const typeTag = document.getElementById('ai-review-type-tag');
  if (typeTag) typeTag.textContent = typeName;

  const wsHead = document.getElementById('workspace-contract-head');
  if (wsHead) wsHead.textContent = '📄 合同原文 · ' + title;

  const wsMeta = document.getElementById('workspace-contract-meta');
  if (wsMeta) {
    const score = contract.risk === 'high' ? '85' : contract.risk === 'low' ? '35' : '65';
    wsMeta.textContent =
      '版本 2 · 提交人：' + (contract.creator || '—') + ' · ' + (contract.time || '—') +
      ' | 风险评分：' + score + '/100（' + riskName + '）';
  }

  const revHead = document.getElementById('revision-contract-head');
  if (revHead) revHead.textContent = contract.no + ' ' + (contract.name || '') + ' · v1 → v2';

  const aiScore = document.getElementById('detail-ai-score');
  if (aiScore) {
    const score = contract.risk === 'high' ? '85' : contract.risk === 'low' ? '35' : '65';
    aiScore.textContent = score;
  }
  const aiRiskLine = document.getElementById('detail-ai-risk-line');
  if (aiRiskLine) {
    const high = contract.risk === 'high' ? 3 : contract.risk === 'low' ? 0 : 2;
    const med = contract.risk === 'low' ? 0 : 1;
    aiRiskLine.textContent = high + ' 项高风险 · ' + med + ' 项中风险';
  }
  const aiRiskLabel = document.getElementById('detail-ai-risk-label');
  if (aiRiskLabel) aiRiskLabel.textContent = riskName;
}

function openReviewWorkspace(contractNo) {
  sessionStorage.setItem('current_contract_no', contractNo);
  const c = contracts.find((x) => x.no === contractNo);
  if (c?.flowType) sessionStorage.setItem('current_contract_flow', c.flowType);
  switchPage('review-workspace');
  applyWorkspaceFlowTabs(sessionStorage.getItem('current_contract_flow') || 'standard');
  switchStage('legal');
  renderContractContext(c);
}

function backFromContractDetail() {
  const ret = sessionStorage.getItem('approval_history_return') || 'contracts';
  switchPage(ret === 'contract-detail' ? 'contracts' : ret);
}

// 合同详情
function showContractDetail(no, returnPage) {
  sessionStorage.setItem('current_contract_no', no);
  const activePage = document.querySelector('.page.active')?.id?.replace('page-', '') || 'contracts';
  sessionStorage.setItem('approval_history_return', returnPage || activePage);
  const c = contracts.find((x) => x.no === no);
  if (c?.flowType) sessionStorage.setItem('current_contract_flow', c.flowType);
  switchPage('contract-detail');
  renderContractContext(c);
}

/** 从合同上下文打开审批历史（非独立菜单） */
function showApprovalHistory(contractNo) {
  const c = contracts.find((x) => x.no === contractNo);
  if (!c) {
    showToast('未找到合同 ' + contractNo);
    return;
  }
  const activePage = document.querySelector('.page.active')?.id?.replace('page-', '') || 'contracts';
  sessionStorage.setItem('approval_history_contract', contractNo);
  sessionStorage.setItem('approval_history_return', activePage);
  renderApprovalHistory(c);
  switchPage('approval-history');
}

function showApprovalHistoryFromDetail() {
  const no = sessionStorage.getItem('current_contract_no') || 'CTR-20240115-0001';
  sessionStorage.setItem('approval_history_return', 'contract-detail');
  showApprovalHistory(no);
}

function backFromApprovalHistory() {
  const returnPage = sessionStorage.getItem('approval_history_return') || 'contracts';
  const contractNo = sessionStorage.getItem('approval_history_contract');
  if (returnPage === 'contract-detail' && contractNo) {
    showContractDetail(contractNo);
    return;
  }
  switchPage(returnPage === 'approval-history' ? 'contracts' : returnPage);
}

function renderApprovalHistory(contract) {
  const flowType = contract.flowType || (contract.amount >= 1000000 ? 'special' : contract.amount >= 100000 ? 'standard' : 'simple');
  const flowNames = { simple: '简易流程', standard: '标准流程', special: '特殊流程' };
  const titleEl = document.getElementById('approval-history-title');
  const metaEl = document.getElementById('approval-history-meta');
  const tagEl = document.getElementById('approval-history-flow-tag');
  if (titleEl) titleEl.textContent = contract.no + ' ' + contract.name;
  if (metaEl) {
    metaEl.textContent = '提交人：' + (contract.creator || '—') + ' | 提交时间：' + (contract.time || '—') + ' | 当前节点：' + (contract.approvalStatus || contract.statusName || '—');
  }
  if (tagEl) tagEl.textContent = flowNames[flowType] || '标准流程';

  const stepsEl = document.getElementById('approval-history-steps');
  const recordsEl = document.getElementById('approval-history-records');
  if (!stepsEl || !recordsEl) return;

  const nodeSets = {
    simple: ['起草', '部门主管', '法务快审', '用印', '归档'],
    standard: ['起草', '部门主管', '法务审核', '财务审核', '高管审批', '用印签署'],
    special: ['起草', '部门主管', '法务审核', '财务审核', '高管审批', '董事会', '用印签署'],
  };
  const nodes = nodeSets[flowType] || nodeSets.standard;
  const currentNode = contract.approvalStatus || '';
  let activeIdx = nodes.findIndex((n) => currentNode.indexOf(n.replace('快审', '').replace('审核', '')) >= 0 || currentNode.indexOf(n) >= 0);
  if (activeIdx < 0) {
    if (contract.status === 'approved' || contract.status === 'signed' || contract.status === 'archived') activeIdx = nodes.length;
    else if (contract.status === 'pending') activeIdx = Math.min(2, nodes.length - 1);
    else activeIdx = 0;
  }

  let stepsHtml = '';
  nodes.forEach((label, i) => {
    const completed = i < activeIdx;
    const active = i === activeIdx && contract.status === 'pending';
    const cls = completed ? 'completed' : active ? 'active' : '';
    const lineCls = completed ? 'completed' : '';
    if (i > 0) stepsHtml += '<div class="flow-step-line ' + lineCls + '"></div>';
    stepsHtml += '<div class="flow-step ' + cls + '"><div class="step-dot">' + (completed ? '✓' : i + 1) + '</div><div class="step-label">' + label;
    if (active) stepsHtml += '<br><span style="font-size:11px;color:var(--primary)">待处理</span>';
    else if (completed && i === 1) stepsHtml += '<br><span style="font-size:11px;color:var(--gray-400)">' + (contract.creator || '') + ' ✓</span>';
    stepsHtml += '</div></div>';
  });
  stepsEl.innerHTML = stepsHtml;

  const sampleRecords = [
    { node: '部门主管', who: contract.creator || '张三', action: 'green', actionText: '通过', comment: '同意，注意交付周期和验收标准', time: contract.time || '—', duration: '5 分钟' },
    { node: flowType === 'simple' ? '法务快审' : '法务审核', who: '法务部', action: activeIdx > 2 ? 'green' : 'yellow', actionText: activeIdx > 2 ? '通过' : '待处理', comment: activeIdx > 2 ? 'AI 审查风险已提示，整体可签署。' : '—', time: activeIdx > 2 ? '—' : '—', duration: activeIdx > 2 ? '4 小时' : '—' },
  ];
  if (flowType !== 'simple') {
    sampleRecords.push({ node: '财务审核', who: '财务部', action: activeIdx > 3 ? 'green' : 'yellow', actionText: activeIdx > 3 ? '通过' : '待处理', comment: '—', time: '—', duration: '—' });
  }
  if (flowType === 'special') {
    sampleRecords.push({ node: '董事会', who: '董事会办公室', action: currentNode.indexOf('董事会') >= 0 ? 'yellow' : 'gray', actionText: currentNode.indexOf('董事会') >= 0 ? '待处理' : '未到达', comment: '—', time: '—', duration: '—' });
  }
  recordsEl.innerHTML = sampleRecords.map((r) => '<tr><td>' + r.node + '</td><td>' + r.who + '</td><td><span class="tag tag-' + r.action + '">' + r.actionText + '</span></td><td>' + r.comment + '</td><td>' + r.time + '</td><td>' + r.duration + '</td></tr>').join('');

  document.getElementById('page-title').textContent = '审批历史';
  document.getElementById('page-breadcrumb').textContent = '合同 / ' + contract.no + ' / 审批历史';
}

// 审批详情
function showApprovalDetail() {
  showModal('approval-detail');
}

// 审批操作
let currentAction = 'approve';
function approveItem(btn, action) {
  currentAction = action;
  const title = action === 'approve' ? '审批通过' : action === 'reject' ? '审批拒绝' : '审批退回';
  document.getElementById('approval-modal-title').textContent = title;
  showModal('approval');
}

function setModalAction(action) {
  currentAction = action;
  document.querySelectorAll('[id^="modal-action-"]').forEach(b => b.style.opacity = '0.5');
  document.getElementById('modal-action-' + action).style.opacity = '1';
}

function setComment(text) {
  document.getElementById('approval-comment').value = text;
}

function confirmApproval() {
  hideModal('approval');
  const actionText = currentAction === 'approve' ? '通过' : currentAction === 'reject' ? '拒绝' : '退回';
  showToast('审批' + actionText + '成功');
  if (currentAction === 'return') {
    setTimeout(function() { switchPage('revision-workspace'); }, 800);
    return;
  }
  // 减少待办计数
  const count = document.getElementById('notif-count');
  state.approvalCount = Math.max(0, parseInt(count.textContent) - 1);
  count.textContent = state.approvalCount;
  persistState();
}

function batchApprove() {
  const checked = document.querySelectorAll('.approval-check:checked');
  if (checked.length === 0) {
    showToast('请先勾选要审批的合同');
    return;
  }
  currentAction = 'approve';
  document.getElementById('approval-modal-title').textContent = `批量通过 (${checked.length} 份)`;
  showModal('approval');
}

// 合同操作

// ====== 模板选择面板 ======
function showTemplateSelector() {
  const templates = [
    { id: 1, name: '标准采购合同', category: 'purchase', version: 'v3.2', vars: '{金额},{相对方},{交货期},{质保期}' },
    { id: 2, name: '销售合同模板', category: 'sales', version: 'v2.1', vars: '{金额},{相对方},{付款方式},{交付日期}' },
    { id: 3, name: '劳务合同模板', category: 'labor', version: 'v1.5', vars: '{岗位},{薪资},{合同期限},{工作地点}' },
    { id: 4, name: '保密协议(NDA)', category: 'nda', version: 'v2.0', vars: '{保密期限},{相对方},{保密范围}' },
    { id: 5, name: '合作合同模板', category: 'cooperation', version: 'v1.8', vars: '{合作内容},{出资比例},{利润分配},{合作期限}' },
  ];
  
  const list = document.getElementById('template-selector-list');
  if (!list) {
    // 创建模板选择面板
    const panel = document.createElement('div');
    panel.id = 'template-selector-panel';
    panel.style.cssText = 'background:var(--gray-50);border-radius:10px;padding:16px;margin:16px 0;border:1px solid var(--gray-200);display:none';
    panel.innerHTML = `
      <div style="font-size:14px;font-weight:600;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between">
        <span>📋 选择合同模板</span>
        <button class="btn btn-outline btn-sm" onclick="document.getElementById('template-selector-panel').style.display='none'">✕ 关闭</button>
      </div>
      <div style="margin-bottom:12px">
        <input class="form-input" placeholder="搜索模板名称..." style="width:100%" oninput="filterTemplates(this.value)">
      </div>
      <div id="template-selector-list" style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px"></div>
    `;
    document.querySelector('#page-create .card-body').insertBefore(panel, document.querySelector('#page-create .card-body').children[1]);
  }
  
  document.getElementById('template-selector-panel').style.display = 'block';
  renderTemplateList(templates);
}

function renderTemplateList(templates) {
  const list = document.getElementById('template-selector-list');
  list.innerHTML = templates.map(t => `
    <div class="kanban-card" style="cursor:pointer;padding:12px;text-align:left" onclick="selectTemplate(${t.id})">
      <div style="font-size:13px;font-weight:600;margin-bottom:4px">${t.name}</div>
      <div style="font-size:11px;color:var(--gray-500);margin-bottom:6px">${t.category} · ${t.version}</div>
      <div style="font-size:10px;color:var(--primary)">可变字段: ${t.vars}</div>
    </div>
  `).join('');
}

function filterTemplates(keyword) {
  const allTemplates = [
    { id: 1, name: '标准采购合同', category: 'purchase', version: 'v3.2', vars: '{金额},{相对方},{交货期},{质保期}' },
    { id: 2, name: '销售合同模板', category: 'sales', version: 'v2.1', vars: '{金额},{相对方},{付款方式},{交付日期}' },
    { id: 3, name: '劳务合同模板', category: 'labor', version: 'v1.5', vars: '{岗位},{薪资},{合同期限},{工作地点}' },
    { id: 4, name: '保密协议(NDA)', category: 'nda', version: 'v2.0', vars: '{保密期限},{相对方},{保密范围}' },
    { id: 5, name: '合作合同模板', category: 'cooperation', version: 'v1.8', vars: '{合作内容},{出资比例},{利润分配},{合作期限}' },
  ];
  const filtered = keyword ? allTemplates.filter(t => t.name.includes(keyword) || t.category.includes(keyword)) : allTemplates;
  renderTemplateList(filtered);
}

function selectTemplate(templateId) {
  // 丰富模板数据（条款级内容，含实际业务文风）
  const templates = {
    1: { name: '标准采购合同', type: 'purchase', title: '标准采购合同', category: 'purchase',
      content: '第一条 采购内容\n甲方向乙方采购 [产品名称] [数量]，具体配置详见附件一《设备清单》。\n\n第二条 合同金额与支付方式\n合同总金额为人民币 [金额] 元（含税），税率为 [税率]%。\n\n第三条 付款条件\n甲方在合同签订后 5 个工作日内支付合同总额的 30% 作为预付款。剩余款项在验收合格后 30 日内支付。\n\n第四条 违约责任\n乙方未按约定时间交付，每逾期一日按合同总额的 0.05%（不超过 5%）支付违约金。乙方违约需赔偿甲方直接损失，赔偿总额不超过合同总额的 30%。\n\n第五条 保密条款\n双方对合同履行过程中知悉的对方商业秘密负有保密义务，保密期限为合同终止后 3 年。\n\n第六条 管辖约定\n本合同的争议由甲方所在地人民法院管辖。\n\n第七条 质保条款\n乙方提供 12 个月的质量保证，质保期内因产品质量问题导致的维修、更换费用由乙方承担。质保金为合同总额的 5%。',
      vars: '{金额},{相对方},{产品名称},{税率}' },
    2: { name: '标准销售合同', type: 'sales', title: '标准销售合同', category: 'sales',
      content: '第一条 销售内容\n甲方向乙方销售 [产品名称] [数量]，具体规格详见附件。\n\n第二条 合同金额\n合同总金额为人民币 [金额] 元（含税）。\n\n第三条 付款方式\n乙方在合同签订后 5 个工作日内支付全款。\n\n第四条 交付与验收\n甲方在收到全款后 15 个工作日内交付产品。\n\n第五条 违约责任\n甲方逾期交付，每逾期一日按合同总额的 0.05% 支付违约金。',
      vars: '{金额},{相对方},{产品名称},{付款方式},{交付日期}' },
    3: { name: '标准劳务合同', type: 'labor', title: '劳务合同', category: 'labor',
      content: '第一条 劳务内容\n乙方为甲方提供 [劳务类型] 劳务服务。\n\n第二条 合同期限\n本合同有效期自 [开始日期] 至 [结束日期]。\n\n第三条 劳务费用\n劳务费用为人民币 [金额] 元/月。\n\n第四条 付款方式\n甲方每月 15 日前支付上月劳务费用。\n\n第五条 违约责任\n任何一方违约，需赔偿守约方全部直接损失。',
      vars: '{劳务类型},{薪资},{合同期限},{开始日期},{结束日期}' },
    4: { name: '保密协议', type: 'nda', title: '保密协议', category: 'nda',
      content: '第一条 保密信息定义\n本协议所称保密信息包括但不限于商业秘密、技术秘密、经营信息等。\n\n第二条 保密义务\n双方对在合作过程中知悉的对方保密信息负有保密义务。\n\n第三条 保密期限\n保密期限为协议终止后 [保密期限] 年。\n\n第四条 违约责任\n违约方需赔偿守约方全部直接损失。\n\n第五条 争议解决\n本协议的争议由甲方所在地人民法院管辖。',
      vars: '{保密期限},{相对方},{保密范围}' },
    5: { name: '合作合同模板', type: 'cooperation', title: '合作合同', category: 'cooperation',
      content: '第一条 合作内容\n双方就 [合作内容] 达成如下合作协议。\n\n第二条 出资与分工\n甲方出资 [甲方出资比例]%，负责 [甲方分工]。乙方出资 [乙方出资比例]%，负责 [乙方分工]。\n\n第三条 利润分配\n双方按出资比例分配利润。\n\n第四条 合作期限\n本合同有效期自 [开始日期] 至 [结束日期]。\n\n第五条 违约责任\n任何一方违约，需赔偿守约方全部直接损失。',
      vars: '{合作内容},{出资比例},{甲方分工},{乙方分工},{利润分配},{合作期限}' }
  };
  
  const tpl = templates[templateId];
  if (!tpl) { showToast('⚠️ 该模板暂无内容，请选择其他模板'); return; }
  
  // 填充表单
  document.getElementById('new-contract-title').value = tpl.title;
  document.getElementById('new-contract-type').value = tpl.type;
  document.getElementById('new-contract-content').value = tpl.content;
  
  // 锁定模板预填字段（名称 + 类型不可修改）
  lockField('new-contract-title', 'template');
  lockField('new-contract-type', 'template');
  
  // 显示模板变量提示
  if (tpl.vars) {
    const vars = tpl.vars.split(',').map(v => v.trim());
    const list = document.getElementById('template-vars-list');
    list.innerHTML = vars.map(v => `<span style="background:#fff;border:1px solid #ffe082;border-radius:4px;padding:3px 10px;font-size:12px;font-weight:500;color:#92400e">${v}</span>`).join('');
    document.getElementById('template-variable-hints').style.display = 'block';
  }
  
  // 更新指示器 + Toast
  updateModeIndicator('template', tpl.name);
  document.getElementById('mode-indicator-detail').textContent = '— 请填写 ' + tpl.vars + ' 等可变字段';
  showToast('✅ 已选择模板：' + tpl.name + '，请填写可变字段');
  
  // 模板内容区高亮可变字段（闪烁提示）
  const contentArea = document.getElementById('new-contract-content');
  contentArea.style.background = '#fffbeb';
  contentArea.style.borderColor = '#f59e0b';
  setTimeout(() => {
    contentArea.style.background = '';
    contentArea.style.borderColor = '';
  }, 2500);
  
  // 关闭面板
  document.getElementById('template-selector-panel').style.display = 'none';
}

// ====== 草稿恢复 ======
function restoreDraft() {
  const draftStr = localStorage.getItem('contract-draft');
  if (!draftStr) return;
  
  const draft = JSON.parse(draftStr);
  if (!confirm('检测到未提交的草稿（保存于 ' + draft.savedAt + '），是否恢复？')) return;
  
  document.getElementById('new-contract-title').value = draft.title || '';
  document.getElementById('new-contract-type').value = draft.type || '';
  document.getElementById('new-contract-counterparty').value = draft.counterparty || '';
  document.getElementById('new-contract-amount').value = draft.amount || '';
  document.getElementById('new-contract-start').value = draft.startDate || '';
  document.getElementById('new-contract-end').value = draft.endDate || '';
  document.getElementById('new-contract-content').value = draft.content || '';
  
  if (draft.mode) selectCreateMode(draft.mode);
  
  showToast('✅ 草稿已恢复');
}

// ====== 自动保存 ======
autoSaveTimer = null;
function startDraftAutoSave() {
  if (autoSaveTimer) clearInterval(autoSaveTimer);
  autoSaveTimer = setInterval(() => {
    const title = document.getElementById('new-contract-title')?.value;
    if (title) saveDraft();
  }, 300000); // 每 5 分钟
}

function saveDraft() {
  const draft = {
    title: document.getElementById('new-contract-title')?.value || '',
    type: document.getElementById('new-contract-type')?.value || '',
    counterparty: document.getElementById('new-contract-counterparty')?.value || '',
    amount: document.getElementById('new-contract-amount')?.value || '',
    startDate: document.getElementById('new-contract-start')?.value || '',
    endDate: document.getElementById('new-contract-end')?.value || '',
    content: document.getElementById('new-contract-content')?.value || '',
    savedAt: new Date().toLocaleString('zh-CN'),
    mode: currentCreateMode || 'blank'
  };
  localStorage.setItem('contract-draft', JSON.stringify(draft));
  showToast('✅ 草稿已保存（' + draft.savedAt + '）');
  // 更新草稿标记
  const draftBadge = document.getElementById('draft-badge');
  if (draftBadge) {
    draftBadge.style.display = 'inline-flex';
    draftBadge.innerHTML = '<span class="tag tag-yellow" style="font-size:10px">💾 草稿</span>';
  }
}

function submitContract() {
  const title = document.getElementById('new-contract-title').value;
  const type = document.getElementById('new-contract-type').value;
  const counterparty = document.getElementById('new-contract-counterparty').value;
  const amount = document.getElementById('new-contract-amount').value;
  const startDate = document.getElementById('new-contract-start').value;
  const endDate = document.getElementById('new-contract-end').value;
  const content = document.getElementById('new-contract-content').value;
  
  // 表单验证
  if (!title || !type || !counterparty || !amount) {
    showToast('⚠️ 请填写必填项（合同名称、类型、相对方、金额）');
    return;
  }
  
  // 金额校验
  if (parseFloat(amount) <= 0) {
    showToast('⚠️ 合同金额必须大于 0');
    return;
  }
  
  // 生成合同编号
  const now = new Date();
  const dateStr = now.toISOString().slice(0,10).replace(/-/g,'');
  const seq = String(Math.floor(Math.random() * 9000) + 1000);
  const contractNo = 'CTR-' + dateStr + '-' + seq;
  
  // 合同类型名称映射
  const typeNames = {
    'purchase': '采购合同', 'sales': '销售合同', 'labor': '劳务合同',
    'nda': '保密协议', 'cooperation': '合作合同', 'legal-standard': '法务制式合同'
  };
  
  const amountNum = parseFloat(amount);
  const flowType = typeof resolveFlowType === 'function'
    ? resolveFlowType(type, amountNum)
    : (amountNum >= 1000000 ? 'special' : amountNum >= 100000 ? 'standard' : 'simple');
  const flowTypeNames = { special: '特殊流程', standard: '标准流程', simple: '简易流程' };
  
  // 获取引用来源（如果有）
  const referencedFrom = localStorage.getItem('contract-referenced-from') || '';
  if (referencedFrom) localStorage.removeItem('contract-referenced-from');
  
  const riskByFlow = { simple: 'low', standard: 'medium', special: 'high' };
  const risk = riskByFlow[flowType] || 'low';
  const contract = normalizeContract({
    id: Date.now(),
    no: contractNo,
    name: title,
    title: title,
    type: type,
    typeName: typeNames[type] || type,
    counterparty: counterparty,
    amount: amountNum,
    content: content || '',
    status: 'pending',
    statusName: '待审批',
    approvalStatus: flowType === 'simple' ? '部门主管审批中' : '法务审核中',
    risk: risk,
    riskName: { low: '低风险', medium: '中风险', high: '高风险' }[risk],
    flowType: flowType,
    flowTypeName: flowTypeNames[flowType],
    creator: '张三',
    time: now.toLocaleString('zh-CN'),
    startDate: startDate || now.toISOString().slice(0, 10),
    endDate: endDate || '',
    createMode: currentCreateMode || 'blank',
    referencedFrom: referencedFrom,
  });
  sessionStorage.setItem('current_contract_no', contractNo);
  sessionStorage.setItem('current_contract_flow', flowType);
  contracts.unshift(contract);
  persistState();
  addAuditLog('提交合同', contractNo, flowTypeNames[flowType]);
  
  // 清除草稿
  clearDraft();
  stopDraftAutoSave();
  
  var flowNodes = {
    simple: ['AI 初筛', '部门主管审批', '法务快审', '用印', '归档'],
    standard: ['AI 初筛', '法务评审', '财务评审', '高管审批', '用印', '归档'],
    special: ['AI 初筛', '法务评审', '财务评审', '高管审批', '董事会审批', '用印', '归档']
  };
  showFlowMatchModal(contractNo, flowTypeNames[flowType], flowNodes[flowType] || flowNodes.standard);
  renderContractContext(contract);
  setTimeout(function() { switchPage('ai-review'); }, 1200);
}

// Toast

function delegateApproval(btn) {
  showToast('👤 委托：V1 原型示意，生产环境 V1.1 实现');
}
function markAiFeedback(type, btn) {
  var labels = { false_positive: 'AI 误报', false_negative: 'AI 漏报' };
  var item = btn.closest('.risk-item');
  if (item && type === 'false_positive') item.style.opacity = '0.55';
  showToast('已记录「' + (labels[type] || type) + '」');
}
function showFlowMatchModal(contractNo, flowTypeName, nodes) {
  const ft = flowTypeName.indexOf('简易') >= 0 ? 'simple' : flowTypeName.indexOf('特殊') >= 0 ? 'special' : 'standard';
  sessionStorage.setItem('current_contract_flow', ft);
  var el = document.getElementById('flow-match-modal-body');
  if (!el) {
    showToast('✅ 合同 ' + contractNo + ' 已提交 · ' + flowTypeName);
    return;
  }
  el.innerHTML = '<p style="margin-bottom:12px"><strong>匹配流程：</strong>' + flowTypeName + '</p><ol style="margin-left:20px;line-height:2">' +
    nodes.map(function(n) { return '<li>' + n + '</li>'; }).join('') + '</ol>';
  showModal('flow-match');
}
// 起草方式选择 ======
let currentCreateMode = 'blank';

function resetCreateMode() {
  // 清除所有模式相关的预填/锁定
  unlockAllFields();
  document.getElementById('template-selector-panel')?.remove();
  document.getElementById('history-selector-panel')?.remove();
  document.getElementById('template-variable-hints').style.display = 'none';
  document.getElementById('history-ref-note').style.display = 'none';
  document.getElementById('mode-reset-btn').style.display = 'none';
  // 清空表单
  document.getElementById('new-contract-title').value = '';
  document.getElementById('new-contract-type').value = '';
  document.getElementById('new-contract-counterparty').value = '';
  document.getElementById('new-contract-amount').value = '';
  document.getElementById('new-contract-start').value = '';
  document.getElementById('new-contract-end').value = '';
  document.getElementById('new-contract-content').value = '';
  document.getElementById('counterparty-credit-info').style.display = 'none';
  // 切回空白模式
  selectCreateMode('blank');
}

function unlockAllFields() {
  const title = document.getElementById('new-contract-title');
  const type = document.getElementById('new-contract-type');
  const counterparty = document.getElementById('new-contract-counterparty');
  const amount = document.getElementById('new-contract-amount');
  const start = document.getElementById('new-contract-start');
  const end = document.getElementById('new-contract-end');
  const content = document.getElementById('new-contract-content');
  
  [title, type, counterparty, amount, start, end, content].forEach(f => {
    if (f) { f.disabled = false; f.classList.remove('field-locked'); }
  });
  // 清除标签上的锁定标记
  document.querySelectorAll('.form-label .field-mode-badge').forEach(b => b.remove());
  // 清除 form-group 上的 label 锁定样式
  document.querySelectorAll('.field-locked-label').forEach(el => el.classList.remove('field-locked-label'));
}

function lockField(id, badgeType) {
  const f = document.getElementById(id);
  if (!f) return;
  f.disabled = true;
  f.classList.add('field-locked');
  // 给前面的 label 加 badge
  const label = f.closest('.form-group')?.querySelector('.form-label');
  if (label) {
    label.classList.add('field-locked-label');
    // 去掉已有的 badge
    label.querySelectorAll('.field-mode-badge').forEach(b => b.remove());
    if (badgeType) {
      const badge = document.createElement('span');
      badge.className = 'field-mode-badge badge-' + badgeType;
      badge.textContent = badgeType === 'template' ? '📋 模板预填' : '📚 历史引用';
      label.appendChild(badge);
    }
  }
}

function updateModeIndicator(mode, detail) {
  const modes = { blank: '空白起草', template: '模板起草', history: '历史引用', 'ai-parse': '智能起草' };
  const details = {
    blank: '— 手动填写所有字段，自由定义合同内容',
    template: '— 选择模板后，只填写可变字段',
    history: '— 引用历史合同，金额需重新填写',
    'ai-parse': '— 上传文件由 AI 自动解析'
  };
  document.getElementById('mode-indicator-text').textContent = modes[mode] || mode;
  document.getElementById('mode-indicator-detail').textContent = details[mode] || '';
  const indicator = document.getElementById('create-mode-indicator');
  const resetBtn = document.getElementById('mode-reset-btn');
  
  // 每种模式不同的视觉风格
  const styles = {
    blank:    { bg: '#eff6ff', bd: '#93c5fd', color: '#1d4ed8' },  // 蓝色：自由
    template: { bg: '#fff8e1', bd: '#fcd34d', color: '#92400e' },  // 琥珀：模板指导
    history:  { bg: '#ecfdf5', bd: '#6ee7b7', color: '#065f46' },  // 绿色：回收复用
    'ai-parse': { bg: '#f5f3ff', bd: '#c4b5fd', color: '#6d28d9' } // 紫色：AI智能
  };
  const s = styles[mode] || styles.blank;
  indicator.style.background = s.bg;
  indicator.style.borderColor = s.bd;
  indicator.style.color = s.color;
  
  if (mode === 'blank') {
    resetBtn.style.display = 'none';
  } else {
    resetBtn.style.display = 'inline';
  }
}

function selectCreateMode(mode) {
  currentCreateMode = mode;
  
  // 更新四张模式卡的选中状态
  document.querySelectorAll('.create-mode-card').forEach(card => {
    card.style.borderColor = 'var(--gray-200)';
    card.style.background = '';
  });
  const activeCard = document.querySelector('.create-mode-card[data-mode="' + mode + '"]');
  if (activeCard) {
    activeCard.style.borderColor = 'var(--primary)';
    activeCard.style.background = '#eff6ff';
  }
  
  // 重置所有锁定和提示
  unlockAllFields();
  document.getElementById('template-variable-hints').style.display = 'none';
  document.getElementById('history-ref-note').style.display = 'none';
  
  // 先更新指示器
  updateModeIndicator(mode);
  
  if (mode === 'template') {
    showToast('📋 已选择模板起草，请选择模板');
    showTemplateSelector();
  } else if (mode === 'history') {
    showToast('📚 已选择历史引用，请搜索历史合同');
    showHistorySelector();
  } else if (mode === 'ai-parse') {
    showToast('🤖 已选择智能起草，请上传合同文件');
    const zone = document.getElementById('upload-zone');
    zone.scrollIntoView({behavior:'smooth'});
    zone.style.borderColor = 'var(--primary)';
    zone.style.background = '#eff6ff';
    setTimeout(() => {
      zone.style.borderColor = 'var(--gray-300)';
      zone.style.background = '';
    }, 2000);
  } else {
    // 空白起草 — 清空表单 + 解锁
    showToast('✅ 已选择空白起草，请填写基本信息');
    document.getElementById('new-contract-title').value = '';
    document.getElementById('new-contract-type').value = '';
    document.getElementById('new-contract-content').value = '';
    document.getElementById('template-selector-panel')?.remove();
  }
}

// ====== 文件上传与预处理 ======
function handleFileSelect(input) {
  const list = document.getElementById('upload-file-list');
  list.innerHTML = '';
  const maxSize = 50 * 1024 * 1024; // 50MB
  let hasError = false;
  
  for (const file of input.files) {
    // 文件大小校验
    if (file.size > maxSize) {
      showToast('⚠️ 文件 ' + file.name + ' 超过 50MB 限制');
      hasError = true;
      continue;
    }
    
    // 文件类型校验
    const ext = file.name.split('.').pop().toLowerCase();
    const allowed = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'tiff', 'bmp'];
    if (!allowed.includes(ext)) {
      showToast('⚠️ 不支持的文件类型：' + ext);
      hasError = true;
      continue;
    }
    
    const icons = { pdf: '📄', doc: '📝', docx: '📝', jpg: '🖼️', jpeg: '🖼️', png: '🖼️', tiff: '📑', bmp: '🖼️' };
    const item = document.createElement('div');
    item.className = 'upload-file-item';
    const sizeStr = file.size > 1024 * 1024 ? (file.size / (1024*1024)).toFixed(1) + 'MB' : (file.size/1024).toFixed(1) + 'KB';
    item.innerHTML = `<span>${icons[ext]||'📎'} ${file.name}</span> <span style="color:var(--gray-400);font-size:11px">${sizeStr}</span> <span class="file-remove" onclick="this.parentElement.remove();checkFileList()">✕</span>`;
    list.appendChild(item);
  }
  
  if (!hasError && input.files.length > 0) startPreprocess();
}

function handleFileDrop(e) {
  const files = e.dataTransfer.files;
  const fakeInput = { files };
  handleFileSelect(fakeInput);
}

function checkFileList() {
  const list = document.getElementById('upload-file-list');
  if (!list.children.length) {
    document.getElementById('preprocess-panel').style.display = 'none';
  }
}

function startPreprocess() {
  const panel = document.getElementById('preprocess-panel');
  panel.style.display = 'block';
  const steps = document.querySelectorAll('#preprocess-steps .preprocess-step');
  const bar = document.getElementById('preprocess-bar');
  const pct = document.getElementById('preprocess-pct');
  steps.forEach(s => { s.className = 'preprocess-step'; s.querySelector('.step-status').textContent = '等待中'; });
  bar.style.width = '0%'; pct.textContent = '0%';
  
  const durations = [800, 1200, 600, 900]; // ms per step
  let cumulative = 0;
  steps.forEach((step, i) => {
    setTimeout(() => {
      step.classList.add('active');
      step.querySelector('.step-status').textContent = '进行中...';
    }, cumulative);
    cumulative += durations[i];
    setTimeout(() => {
      step.classList.remove('active');
      step.classList.add(i === 3 && Math.random() > 0.9 ? 'error' : 'done');
      const status = step.querySelector('.step-status');
      status.textContent = step.classList.contains('error') ? '⚠️ 需人工复核' : '✓ 完成';
      bar.style.width = ((i+1)*25) + '%';
      pct.textContent = ((i+1)*25) + '%';
      if (i === 3) {
        const ocr = document.getElementById('ocr-status');
        ocr.style.display = 'block';
        ocr.style.background = '#f0fdf4';
        ocr.style.color = 'var(--success)';
        ocr.innerHTML = '✅ OCR 识别完成 · 识别精度 98.5% · 检测到 1 处疑似错别字';
      }
    }, cumulative);
  });
}

// 配置标签切换
function switchConfigTab(el, tab) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('config-thresholds').style.display = tab === 'thresholds' ? 'block' : 'none';
  document.getElementById('config-approvers').style.display = tab === 'approvers' ? 'block' : 'none';
}

// 操作引导
function showTour() {
  document.getElementById('tour-hint').style.display = 'flex';
}
function closeTour() {
  document.getElementById('tour-hint').style.display = 'none';
}

// ====== 评审工作台函数（增强版） ======
workspaceConfirmed = 0;
let workspaceFindings = {};  // panelId -> {status, riskLevel, description, suggestion, legalBasis}
let currentEditPanelId = null;
let workspaceDirty = false;
autoSaveTimer = null;

function scrollToPanel(panelId) {
  const panel = document.getElementById(panelId);
  if (panel) {
    panel.scrollIntoView({ behavior: 'smooth', block: 'center' });
    panel.style.boxShadow = '0 0 0 3px var(--primary)';
    panel.style.transform = 'scale(1.01)';
    setTimeout(() => { panel.style.boxShadow = ''; panel.style.transform = ''; }, 2000);
  }
}

function highlightClause(el) {
  document.querySelectorAll('.clause-text').forEach(c => c.style.background = '');
  el.style.background = '#eff6ff';
  setTimeout(() => { el.style.background = el.dataset.clause.indexOf('4') === 0 ? '#fff5f5' : (el.dataset.clause.indexOf('3') === 0 || el.dataset.clause.indexOf('6') === 0 ? '#fffdf5' : ''); }, 2000);
}

// 划选批注工具栏
function showAnnotationToolbar(event, clauseEl, clauseId) {
  const selection = window.getSelection();
  if (!selection || selection.toString().trim().length === 0) return;
  const toolbar = document.getElementById('annotation-toolbar');
  const rect = selection.getRangeAt(0).getBoundingClientRect();
  const leftPanel = document.getElementById('workspace-left');
  const panelRect = leftPanel.getBoundingClientRect();
  toolbar.style.left = (rect.left - panelRect.left + rect.width/2 - 90) + 'px';
  toolbar.style.top = (rect.top - panelRect.top - 40) + 'px';
  toolbar.classList.add('show');
  toolbar.dataset.clauseId = clauseId;
  toolbar.dataset.selectedText = selection.toString();
  setTimeout(() => {
    document.addEventListener('click', function hideToolbar(e) {
      if (!toolbar.contains(e.target)) {
        toolbar.classList.remove('show');
        document.removeEventListener('click', hideToolbar);
      }
    });
  }, 100);
}

function addAnnotation(type) {
  const toolbar = document.getElementById('annotation-toolbar');
  const clauseId = toolbar.dataset.clauseId;
  const text = toolbar.dataset.selectedText;
  toolbar.classList.remove('show');
  const types = { risk: '🔴 标记风险', comment: '💬 添加批注', suggestion: '✏️ 修改建议' };
  showToast(`${types[type]}：已记录在「${clauseId}」条款（"${text.substring(0, 20)}..."）`);
  // 在新增评审区域预填
  const ta = document.getElementById('new-finding-text');
  ta.value = `[${types[type]}] 条款 ${clauseId}："${text}"
`;
  ta.focus();
}

// 确认 AI 标记
function confirmFinding(btn, panelId) {
  const panel = document.getElementById(panelId);
  const status = panel.querySelector('.finding-status');
  panel.style.borderColor = 'var(--success)';
  panel.style.background = '#f0fdf4';
  status.textContent = '状态：✓ 法务已确认';
  status.style.color = 'var(--success)';
  
  // 更新对应条款状态
  updateClauseStatus(panelId, 'confirmed');
  
  // 显示应用修改按钮
  panel.querySelectorAll('[class*="btn-apply"]').forEach(b => {
    if (b.style.display === 'none') b.style.display = '';
  });
  
  workspaceConfirmed++;
  workspaceDirty = true;
  updateWorkspaceProgress();
  
  // 保存到 findings
  workspaceFindings[panelId] = {
    ...workspaceFindings[panelId],
    status: 'confirmed',
    suggestion: panel.querySelector('.suggestion-text')?.value || ''
  };
}

// 打开修正弹窗
function openEditModal(panelId) {
  currentEditPanelId = panelId;
  const panel = document.getElementById(panelId);
  const descEl = panel.querySelector('[style*="font-size:12px;color:var(--gray-600)"]');
  const legalEl = panel.querySelector('[style*="font-size:11px;color:var(--primary)"]');
  const suggestionEl = panel.querySelector('.suggestion-text');
  const riskTag = panel.querySelector('.tag-red, .tag-yellow');
  const level = riskTag && riskTag.classList.contains('tag-red') ? 'high' : 'medium';
  
  document.getElementById('edit-risk-level').value = level;
  document.getElementById('edit-risk-desc').value = descEl ? descEl.textContent.trim() : '';
  document.getElementById('edit-legal-basis').value = legalEl ? legalEl.textContent.trim().replace('📖 ','') : '';
  document.getElementById('edit-suggestion').value = suggestionEl ? suggestionEl.value : '';
  
  document.getElementById('edit-finding-modal').classList.add('show');
}

function closeEditModal() {
  document.getElementById('edit-finding-modal').classList.remove('show');
  currentEditPanelId = null;
}

function saveEditFinding() {
  if (!currentEditPanelId) return;
  const panel = document.getElementById(currentEditPanelId);
  const statusEl = panel.querySelector('.finding-status');
  const level = document.getElementById('edit-risk-level').value;
  const desc = document.getElementById('edit-risk-desc').value;
  const suggestion = document.getElementById('edit-suggestion').value;
  const legalBasis = document.getElementById('edit-legal-basis').value;
  
  // 更新面板
  const levelTag = level === 'high' ? 'tag tag-red' : level === 'medium' ? 'tag tag-yellow' : 'tag tag-green';
  const riskTag = panel.querySelector('.tag-red, .tag-yellow, .tag-green');
  if (riskTag) {
    riskTag.className = levelTag;
    riskTag.textContent = level === 'high' ? '高风险' : level === 'medium' ? '中风险' : '低风险';
  }
  
  const descEl = panel.querySelector('[style*="font-size:12px;color:var(--gray-600)"]');
  if (descEl) descEl.textContent = desc;
  
  const legalEl = panel.querySelector('[style*="font-size:11px;color:var(--primary)"]');
  if (legalEl) legalEl.textContent = '📖 ' + legalBasis;
  
  const suggestionEl = panel.querySelector('.suggestion-text');
  if (suggestionEl) suggestionEl.value = suggestion;
  
  statusEl.textContent = '状态：✏️ 人工修正';
  statusEl.style.color = 'var(--primary)';
  panel.style.borderColor = 'var(--primary)';
  
  workspaceFindings[currentEditPanelId] = { status: 'edited', riskLevel: level, description: desc, suggestion, legalBasis };
  workspaceDirty = true;
  
  closeEditModal();
  showToast('修正已保存');
}

// 忽略 AI 标记
function ignoreFinding(panelId) {
  const panel = document.getElementById(panelId);
  panel.style.opacity = '0.5';
  panel.style.borderColor = 'var(--gray-300)';
  panel.querySelector('.finding-status').textContent = '状态：⊘ 法务已忽略';
  panel.querySelector('.finding-status').style.color = 'var(--gray-500)';
  
  updateClauseStatus(panelId, 'ignored');
  workspaceConfirmed++;
  workspaceDirty = true;
  workspaceFindings[panelId] = { status: 'ignored' };
  updateWorkspaceProgress();
}

// 更新条款状态标记
function updateClauseStatus(panelId, status) {
  const clauseMap = {
    'panel-3-1': 'clause-status-3',
    'panel-4-1': 'clause-status-4',
    'panel-4-2': 'clause-status-4',
    'panel-6-1': 'clause-status-6'
  };
  const statusId = clauseMap[panelId];
  if (!statusId) return;
  const el = document.getElementById(statusId);
  if (!el) return;
  el.className = 'clause-status ' + status;
  el.textContent = status === 'confirmed' ? '✓ 已确认' : status === 'ignored' ? '已忽略' : '待审查';
}

// 应用修改建议
function applySuggestion(panelId) {
  const panel = document.getElementById(panelId);
  const suggestionEl = panel.querySelector('.suggestion-text');
  if (!suggestionEl) return;
  showToast('修改建议已保存，将在退回修改时展现给起草人');
  workspaceDirty = true;
}

// 新增评审意见
function addNewFinding() {
  const text = document.getElementById('new-finding-text').value.trim();
  if (!text) { showToast('请输入评审意见'); return; }
  showToast('评审意见已提交');
  document.getElementById('new-finding-text').value = '';
}

// ====== AI 合同问答 ======
function aiQaAsk() {
  const input = document.getElementById('ai-qa-input');
  const question = input.value.trim();
  if (!question) return;
  const history = document.getElementById('ai-qa-history');
  const userDiv = document.createElement('div');
  userDiv.style.marginBottom = '6px';
  userDiv.innerHTML = '<span style="color:var(--primary);font-weight:600">你：</span>' + question;
  history.appendChild(userDiv);
  input.value = '';
  
  const aiDiv = document.createElement('div');
  aiDiv.style.cssText = 'background:var(--gray-50);padding:8px;border-radius:6px;margin-bottom:8px';
  aiDiv.innerHTML = '<span style="color:var(--success);font-weight:600">AI：</span><span style="color:var(--gray-400)">思考中...</span>';
  history.appendChild(aiDiv);
  history.scrollTop = history.scrollHeight;
  
  setTimeout(() => {
    const responses = {
      '风险': '该条款存在合规风险：违约金比例过高、赔偿范围无上限。依据《民法典》第 584-585 条，法院可能调减违约金并限制赔偿范围。建议修改违约金为 0.05%/日并设上限 5%，限定赔偿为直接损失。',
      '修改': '建议分两步修改：① 将违约金从 0.5%/日 降至 0.05%/日，上限不超过合同总额 5%；② 删除"含间接损失、利润损失"，明确为"直接损失"，赔偿上限为合同总额 30%。',
      '法条': '相关法条：①《民法典》第 584 条（损失赔偿计算规则）② 第 585 条（违约金调整规则）③《民事诉讼法》第 35 条（协议管辖选择权）。',
      '行业': '行业标准条款：违约金通常为 0.03%-0.05%/日，设上限 5-10%；赔偿上限为合同总额 20-50%；管辖约定为甲方所在地。该合同所有条款均偏离行业标准。',
    };
    let key = '风险';
    if (question.includes('修改')) key = '修改';
    else if (question.includes('法条')) key = '法条';
    else if (question.includes('行业')) key = '行业';
    aiDiv.innerHTML = '<span style="color:var(--success);font-weight:600">AI：</span>' + responses[key];
  }, 800);
}
function aiQaQuick(q) {
  document.getElementById('ai-qa-input').value = q;
  aiQaAsk();
}

// ====== 批注模式切换 ======
let currentAnnotationMode = 'inline';
function switchAnnotationMode(mode) {
  currentAnnotationMode = mode;
  document.querySelectorAll('.annotation-mode-btn').forEach(b => b.classList.remove('active'));
  const btnId = 'ann-' + mode;
  const btn = document.getElementById(btnId);
  if (btn) btn.classList.add('active');
  
  const toolbar = document.getElementById('annotation-toolbar');
  if (mode === 'inline') {
    toolbar.style.display = '';
    showToast('已切换为原文内嵌模式');
  } else if (mode === 'sidebar') {
    toolbar.style.display = '';
    showToast('已切换为侧边批注模式（划选文字后在侧边添加批注）');
  } else {
    toolbar.style.display = '';
    showToast('已切换为在线批注模式（类似 Google Docs Suggesting）');
  }
}

// 进度更新
function updateWorkspaceProgress() {
  const pct = Math.round((workspaceConfirmed / 4) * 100);
  document.getElementById('workspace-progress').textContent = workspaceConfirmed + '/4 已确认';
  document.getElementById('workspace-progress-bar').style.width = pct + '%';
  if (workspaceConfirmed >= 4) {
    document.getElementById('btn-approve').disabled = false;
    document.getElementById('btn-conditional').disabled = false;
    document.getElementById('workspace-progress').style.color = 'var(--success)';
    document.getElementById('workspace-progress-bar').classList.remove('yellow');
    document.getElementById('workspace-progress-bar').classList.add('green');
  }
  persistState();
}

// 筛选面板
function filterPanels(level) {
  document.querySelectorAll('.review-panel').forEach(p => { p.style.display = ''; });
  if (level === 'high') document.querySelectorAll('.review-panel:not(.risk-high)').forEach(p => { p.style.display = 'none'; });
  else if (level === 'medium') document.querySelectorAll('.review-panel:not(.risk-medium)').forEach(p => { p.style.display = 'none'; });
  else if (level === 'low') document.querySelectorAll('.review-panel:not(.risk-low)').forEach(p => { p.style.display = 'none'; });
}

// 标记编辑
function markDirty(el) {
  workspaceDirty = true;
}

// 手动保存
function saveWorkspace() {
  const suggestionTexts = {};
  document.querySelectorAll('.suggestion-text').forEach(el => {
    suggestionTexts[el.dataset.panel] = el.value;
  });
  // 模拟保存到后端
  showToast('评审进度已保存');
  document.getElementById('save-indicator').textContent = '💾 已保存';
  document.getElementById('save-indicator').className = 'save-indicator saved';
  workspaceDirty = false;
  persistState();
  setTimeout(() => {
    document.getElementById('save-indicator').textContent = '💾 已自动保存';
    document.getElementById('save-indicator').className = 'save-indicator';
  }, 2000);
}

// 自动保存

function recoverDraft() {
  const draft = loadDraft();
  if (draft) {
    restoreDraft(draft);
    showToast('✅ 已恢复草稿（' + draft.savedAt + '）');
    document.getElementById('btn-restore-draft').style.display = 'none';
    document.getElementById('btn-clear-draft').style.display = 'inline-flex';
    document.getElementById('draft-badge').style.display = 'inline-flex';
    document.getElementById('draft-badge').innerHTML = '<span class="tag tag-yellow" style="font-size:10px">💾 草稿</span>';
  }
}


// [removed duplicate startAutoSave]


// 停止自动保存（离开页面时）
function stopAutoSave() {
  if (autoSaveTimer) { clearInterval(autoSaveTimer); autoSaveTimer = null; }
}

// 启动自动保存（页面加载时）
document.addEventListener('DOMContentLoaded', () => {
  /* workspace autosave via switchStage */;
});
// 修订工作台函数
function acceptRevision(btn) {
  const card = btn.closest('.revision-item-card') || btn.closest('[style*="border-radius:8px"]');
  if (!card) return;
  card.style.borderLeftColor = 'var(--success)';
  card.style.background = '#f0fdf4';
  card.dataset.revisionDone = '1';
  btn.textContent = '✓ 已接受';
  btn.className = 'btn btn-success btn-sm';
  btn.disabled = true;
  if (btn.nextElementSibling) btn.nextElementSibling.style.display = 'none';
  showToast('修改建议已接受');
  updateRevisionProgress();
}

function rejectRevision(btn) {
  const reason = prompt('请输入拒绝原因：', '');
  if (!reason) return;
  const card = btn.closest('.revision-item-card') || btn.closest('[style*="border-radius:8px"]');
  if (!card) return;
  card.style.borderLeftColor = 'var(--gray-400)';
  card.style.opacity = '0.7';
  card.dataset.revisionDone = '1';
  btn.textContent = '✗ 已拒绝';
  btn.className = 'btn btn-outline btn-sm';
  btn.disabled = true;
  if (btn.previousElementSibling) btn.previousElementSibling.style.display = 'none';
  showToast('已拒绝（原因：' + reason + '）');
  updateRevisionProgress();
}

function updateRevisionProgress() {
  const cards = document.querySelectorAll('#page-revision-workspace .revision-item-card');
  const total = cards.length;
  let done = 0;
  cards.forEach((c) => {
    if (c.dataset.revisionDone === '1') done += 1;
  });
  const textEl = document.getElementById('revision-progress-text');
  const fillEl = document.getElementById('revision-progress-fill');
  const summaryEl = document.getElementById('revision-progress-summary');
  if (textEl) textEl.textContent = done + '/' + total + ' 已处理';
  if (fillEl && total > 0) fillEl.style.width = Math.round((done / total) * 100) + '%';
  if (summaryEl) summaryEl.textContent = done + ' 已处理 · ' + (total - done) + ' 待处理';
}


function returnToDrafter() {
  const no = sessionStorage.getItem('current_contract_no') || getActiveContract()?.no;
  if (no) sessionStorage.setItem('current_contract_no', no);
  showToast('合同已退回起草人修改，请前往修订工作台处理');
  setTimeout(() => {
    switchPage('revision-workspace');
    renderContractContext(getActiveContract());
  }, 1000);
}

// ====== 评审阶段切换 ======
let currentReviewStage = 'legal';

function switchStage(stage) {
  if (stage === 'ai') {
    switchPage('ai-review');
    renderContractContext(getActiveContract());
    showToast('AI 初筛在「审查报告」页完成，确认后提交法务评审');
    return;
  }
  currentReviewStage = stage;
  // 更新标签状态
  document.querySelectorAll('#stage-tabs .stage-tab').forEach(tab => {
    tab.classList.toggle('active', tab.dataset.stage === stage);
  });
  // 更新阶段面板显隐
  document.querySelectorAll('.workspace-stage-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === 'stage-' + stage);
  });
  // 停止/重启自动保存
  if (stage === 'legal') {
    stopWorkspaceAutoSave();
    setTimeout(startWorkspaceAutoSave, 1000);
  } else {
    stopWorkspaceAutoSave();
  }
}


// ====== 财务评审函数 ======
function financeApprove() {
  // 保存财务评审结论
  const financeOpinion = document.querySelector('#stage-finance textarea[placeholder*="财务评审意见"]');
  if (financeOpinion && !financeOpinion.value.trim()) {
    showToast('⚠️ 请填写财务评审意见');
    financeOpinion.focus();
    return;
  }
  showToast('✅ 财务评审通过，已进入高管终审阶段');
  document.querySelector('[data-stage=executive]').classList.add('completed');
  document.querySelector('[data-stage=finance]').classList.add('completed');
  // 更新高管面板摘要
  const finSummary = document.querySelector('#stage-executive .finance-summary');
  if (finSummary) finSummary.innerHTML = '<span style="color:var(--success);font-weight:600">✓ 通过</span>';
  setTimeout(() => switchStage('executive'), 1200);
}

function financeConditionalPass() {
  const financeOpinion = document.querySelector('#stage-finance textarea[placeholder*="财务评审意见"]');
  if (!financeOpinion || !financeOpinion.value.trim()) {
    showToast('⚠️ 请填写有条件通过的具体条件');
    financeOpinion?.focus();
    return;
  }
  showToast('⚠️ 有条件通过：高管将看到财务调整建议');
  document.querySelector('[data-stage=executive]').classList.add('completed');
  document.querySelector('[data-stage=finance]').classList.add('completed');
  const finSummary = document.querySelector('#stage-executive .finance-summary');
  if (finSummary) finSummary.innerHTML = '<span style="color:var(--warning);font-weight:600">⚠️ 有条件通过</span>';
  setTimeout(() => switchStage('executive'), 1200);
}

// ====== 高管终审函数 ======
function executiveReject() {
  if (!confirm('确认拒绝此合同？拒绝后流程终止，起草人将收到通知。')) return;
  showToast('❌ 合同已拒绝，流程终止');
  // 更新合同状态
  const contractStatus = document.querySelector('[data-contract-status]');
  if (contractStatus) {
    contractStatus.textContent = '已拒绝';
    contractStatus.className = 'tag tag-red';
  }
  // 记录审计日志
  addAuditLog('高管拒绝', 'CTR-20240115-0001', '合同审批流程已终止');
  setTimeout(() => switchPage('approvals'), 1000);
}


// ====== 模板管理函数 ======
function archiveTemplate(code) {
  if (!confirm('确认废止模板 ' + (code || '') + '？废止后不可被新建合同引用。')) return;
  showToast('✅ 模板 ' + (code || '') + ' 已废止');
}

function publishTemplate(templateId) {
  const btn = (typeof event !== 'undefined' && event && event.target)
    || document.querySelector('#page-templates button[onclick="publishTemplate()"]');
  if (!btn) return;
  btn.textContent = '已提交';
  btn.disabled = true;
  showToast('✅ 模板已提交发布，等待审核');
  const statusEl = btn.closest('.template-card')?.querySelector('.template-status');
  if (statusEl) { statusEl.textContent = '待审批'; statusEl.className = 'tag tag-yellow'; }
}

// ====== AI审查确认 ======
function confirmAIReview() {
  if (!confirm('确认 AI 初筛结论并提交法务评审？')) return;
  const c = getActiveContract();
  const no = c?.no || sessionStorage.getItem('current_contract_no');
  if (no) sessionStorage.setItem('current_contract_no', no);
  sessionStorage.setItem('ai_review_confirmed', no || '1');
  showToast('✅ 审查结论已确认，进入法务评审');
  const aiTab = document.querySelector('[data-stage=ai]');
  if (aiTab) aiTab.classList.add('completed');
  switchPage('review-workspace');
  applyWorkspaceFlowTabs(sessionStorage.getItem('current_contract_flow') || c?.flowType || 'standard');
  switchStage('legal');
  renderContractContext(c);
}

// ====== 条款比对导出 ======
function exportCompareReport() {
  showToast('📄 比对报告已导出为 PDF');
  const blob = new Blob(['合同条款比对报告'], {type:'application/pdf'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = 'compare-report.pdf'; a.click(); URL.revokeObjectURL(a.href);
}

// ====== 黑名单管理 ======
function removeBlacklist(counterpartyId) {
  if (!confirm('确认从黑名单移除此相对方？')) return;
  showToast('✅ 已从黑名单移除');
  const row = event.target.closest('tr');
  if (row) { const s = row.querySelector('.tag-red'); if(s){s.textContent='正常';s.className='tag tag-green';} }
}

function resolveConflict(choice) {
  const names = {legal: '法务意见', ai: 'AI意见'};
  if (!confirm('确认采纳' + names[choice] + '？这将作为最终仲裁结果。')) return;
  showToast('✅ 已采纳' + names[choice] + '，冲突已解决');
  const card = event.target.closest('div[style*="background:#fff3cd"]');
  if (card) {
    card.style.background = '#f0fdf4';
    card.style.borderColor = 'var(--success)';
    const title = card.querySelector('div[style*="font-size:13px;font-weight:600"]');
    if (title) title.innerHTML = '✅ 冲突已解决 — 采纳' + names[choice];
    const btns = card.querySelectorAll('button');
    btns.forEach(b => { b.disabled = true; b.textContent = '已解决'; });
  }
  // Record in localStorage
  const resolved = JSON.parse(localStorage.getItem('conflicts-resolved')||'[]');
  resolved.push({conflictId: 'CTR-20240114-0003', choice: choice, resolvedAt: new Date().toLocaleString('zh-CN')});
  localStorage.setItem('conflicts-resolved', JSON.stringify(resolved));
}

// ====== 冲突升级 ======
function escalateConflict(conflictId) {
  showToast('⚖️ 已升级至法务负责人仲裁');
  const btn = (typeof event !== 'undefined' && event && event.target)
    || document.querySelector('#page-review-center button[onclick*="escalateConflict"]');
  if (!btn) return;
  const card = btn.closest('.conflict-card');
  if (card) {
    const s = card.querySelector('.conflict-status');
    if (s) { s.textContent = '仲裁中'; s.style.color = 'var(--warning)'; }
  }
  btn.disabled = true;
  btn.textContent = '已升级';
}

// ====== AI标记验证 ======
function validateAIMarks(stageId) {
  const panels = document.querySelectorAll('#' + stageId + ' .review-panel').length;
  const handled = document.querySelectorAll('#' + stageId + ' .review-panel .finding-handled').length;
  if (handled < panels) { showToast('⚠️ 还有 ' + (panels - handled) + ' 项 AI 标记未处理'); return false; }
  return true;
}

// ====== 风险标记已处理 ======
function markRiskHandled(riskId) {
  closeRiskDetail();
  showToast('✅ 已标记为已处理');
  const row = document.querySelector('tr[data-risk-id="' + riskId + '"]');
  if (row) { const s = row.querySelector('.tag-yellow, .tag-red'); if(s){s.textContent='已处理';s.className='tag tag-green';} }
}

// ====== 草稿保存（创建页） ======
function saveDraftCreate() {
  const form = document.getElementById('contract-create-form');
  if (!form) return;
  const data = {};
  for (let [k,v] of new FormData(form).entries()) data[k] = v;
  data.savedAt = new Date().toLocaleString('zh-CN'); data.status = '草稿';
  localStorage.setItem('contract-draft', JSON.stringify(data));
  showToast('✅ 草稿已保存');
}

// ====== 修订提交 ======
function saveDraftRevision() {
  const no = sessionStorage.getItem('current_contract_no') || getActiveContract()?.no || 'draft';
  const summary = document.getElementById('revision-summary')?.value || '';
  localStorage.setItem(
    'revision-draft-' + no,
    JSON.stringify({ summary, savedAt: new Date().toLocaleString('zh-CN') })
  );
  showToast('✅ 修订草稿已保存');
}

function submitRevision() {
  const opinion = document.getElementById('revision-summary');
  if (!opinion || !opinion.value.trim()) {
    showToast('⚠️ 请填写修订说明');
    opinion?.focus();
    return;
  }
  const no = sessionStorage.getItem('current_contract_no') || getActiveContract()?.no || 'CTR-20240115-0001';
  showToast('✅ 修订已提交，重新进入 AI 初筛');
  localStorage.setItem(
    'revision-submitted',
    JSON.stringify({
      contractNo: no,
      summary: opinion.value.trim(),
      submittedAt: new Date().toLocaleString('zh-CN'),
      status: '重新评审中',
    })
  );
  sessionStorage.setItem('current_contract_no', no);
  setTimeout(() => switchPage('ai-review'), 800);
}

// ====== 用印确认 ======
function confirmSealAction(contractNo) {
  const no = contractNo || (event?.target?.closest('tr')?.querySelector('code')?.textContent?.trim());
  if (!confirm('确认用印？用印后合同将进入归档流程。')) return;
  showToast('✅ 用印已确认，合同进入归档流程');
  if (no) {
    const c = contracts.find((x) => x.no === no);
    if (c) {
      c.status = 'signed';
      c.statusName = '已用印';
      persistState();
    }
    sessionStorage.setItem('current_contract_no', no);
  }
  const row = event?.target?.closest('tr');
  if (row) { const s = row.querySelector('.tag-yellow'); if(s){s.textContent='已用印';s.className='tag tag-green';} }
  if (no) {
    const stored = JSON.parse(localStorage.getItem('contract-' + no) || '{}');
    stored.sealStatus = 'completed';
    stored.sealedAt = new Date().toLocaleString('zh-CN');
    localStorage.setItem('contract-' + no, JSON.stringify(stored));
  }
}

// ====== 台账导出 ======
function exportLedger(format) {
  showToast('✅ 台账已导出为 ' + format);
  const data = "合同编号,合同名称,相对方,金额,状态\nCTR-20240115-0001,服务器采购合同,XX科技公司,¥2,500,000,生效中";
  const blob = new Blob([data], {type: format==='Excel'?'application/vnd.ms-excel':'text/csv'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = 'ledger-' + new Date().toISOString().slice(0,10) + '.' + (format==='Excel'?'xls':'csv'); a.click(); URL.revokeObjectURL(a.href);
}

// ====== 合同筛选 ======
function filterContractsByDate(type) {
  document.querySelectorAll('#page-contracts .filter-btn').forEach(b => b.classList.remove('active'));
  if (typeof event !== 'undefined' && event?.target) {
    event.target.classList.add('active');
  }
  const now = new Date();
  const list = (typeof contracts !== 'undefined' ? contracts : []).map(normalizeContract);
  let filtered = list;
  if (type === 'expiring') {
    const d = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);
    filtered = list.filter((c) => c.endDate && new Date(c.endDate) <= d && new Date(c.endDate) >= now);
  } else if (type === 'monthly') {
    filtered = list.filter((c) => {
      const raw = c.time || c.createdAt || '';
      const dt = new Date(raw);
      return !isNaN(dt) && dt.getMonth() === now.getMonth();
    });
  }
  showToast('📊 筛选' + (type==='expiring'?'已到期':'本月新增') + '合同 ' + filtered.length + ' 条');
  renderContracts(filtered);
}

// ====== 消息已读 ======
function markAllMessagesRead() {
  const items = document.querySelectorAll('#page-messages .msg-item');
  let count = 0;
  items.forEach(item => {
    if (item.getAttribute('data-unread') === 'true') {
      item.setAttribute('data-unread', 'false');
      item.style.background = '#fff';
      item.style.borderLeftColor = 'var(--gray-200)';
      const tag = item.querySelector('.tag');
      if (tag) { tag.textContent = '已读'; tag.className = 'tag tag-gray'; tag.style.fontSize = '10px'; }
      count++;
    }
  });
  updateMessageBadge();
  showToast('✅ 已将 ' + count + ' 条消息标为已读');
}

function markMessageRead(el) {
  const item = el.closest('.msg-item');
  if (!item || item.getAttribute('data-unread') === 'false') return;
  item.setAttribute('data-unread', 'false');
  item.style.background = '#fff';
  item.style.borderLeftColor = 'var(--gray-200)';
  const tag = item.querySelector('.tag');
  if (tag) { tag.textContent = '已读'; tag.className = 'tag tag-gray'; tag.style.fontSize = '10px'; }
  updateMessageBadge();
}

/** 按消息类型解析目标页；无权限时回退到合同详情（下钻页始终可访问） */
function resolveMessageTargetPage(msgType) {
  const typeRoutes = {
    approval: ['approvals', 'contract-detail'],
    ai: ['ai-review', 'contract-detail'],
    system: ['approvals', 'contract-detail'],
    warning: ['contracts', 'contract-detail'],
  };
  const candidates = typeRoutes[msgType] || ['contracts', 'contract-detail'];
  for (const pageId of candidates) {
    if (canAccessPage(pageId)) return pageId;
  }
  return 'contract-detail';
}

function openMessageDetail(el) {
  const item = el.closest('.msg-item');
  if (!item) return;

  markMessageRead(el);

  const contractNo = item.getAttribute('data-contract');
  const msgType = item.getAttribute('data-type');

  if (!contractNo) return;

  const targetPage = resolveMessageTargetPage(msgType);
  sessionStorage.setItem('current_contract_no', contractNo);
  const c = contracts.find((x) => x.no === contractNo);
  if (c?.flowType) sessionStorage.setItem('current_contract_flow', c.flowType);
  showToast('📄 跳转到 ' + contractNo);
  setTimeout(() => {
    if (targetPage === 'contract-detail') {
      showContractDetail(contractNo);
      return;
    }
    switchPage(targetPage);
    renderContractContext(c);
  }, 300);
}

// ====== 各页列表筛选（P1-01，勿复用 filterContracts） ======
function filterPageTableRows(pageId, searchId, statusId, statusAttr) {
  const page = document.getElementById('page-' + pageId);
  if (!page) return;
  const q = (document.getElementById(searchId)?.value || '').toLowerCase().trim();
  const status = document.getElementById(statusId)?.value || '';
  const rows = page.querySelectorAll('tbody tr');
  let visible = 0;
  rows.forEach((row) => {
    const text = row.textContent.toLowerCase();
    const rowStatus = statusAttr ? row.getAttribute(statusAttr) || row.dataset.status || '' : '';
    const matchQ = !q || text.includes(q);
    const matchS = !status || rowStatus === status || text.includes(status);
    const show = matchQ && matchS;
    row.style.display = show ? '' : 'none';
    if (show) visible += 1;
  });
  showToast('筛选完成：显示 ' + visible + ' / ' + rows.length + ' 条');
}

function filterSealList() {
  filterPageTableRows('seal', 'seal-search', 'seal-status-filter');
}
function filterArchiveList() {
  filterPageTableRows('archives', 'archive-search', 'archive-status-filter');
}
function filterCounterpartyList() {
  filterPageTableRows('counterparties', 'cp-search', 'cp-status-filter');
}
const AUDIT_LOG_SEED = [
  { time: '2024-01-15 14:30', operator: '刘法务', action: '审批通过', target: 'CTR-20240115-0001', detail: '法务评审通过', resource: '合同' },
  { time: '2024-01-15 14:00', operator: '张三', action: '修改', target: 'CTR-20240115-0001', detail: '更新付款条款', resource: '合同' },
  { time: '2024-01-15 10:30', operator: '李四', action: '创建', target: 'CTR-20240115-0002', detail: '新建合同', resource: '合同' },
  { time: '2024-01-15 09:00', operator: '张三', action: '提交合同', target: 'CTR-20240115-0001', detail: '标准流程', resource: '合同' },
];

function auditActionTag(action) {
  const a = String(action || '');
  if (/通过|批准/.test(a)) return '<span class="tag tag-green">' + a + '</span>';
  if (/删除|拒绝/.test(a)) return '<span class="tag tag-red">' + a + '</span>';
  if (/提交|创建/.test(a)) return '<span class="tag tag-blue">' + a + '</span>';
  return '<span class="tag tag-gray">' + a + '</span>';
}

function renderAuditLog() {
  let logs = [];
  try {
    logs = JSON.parse(localStorage.getItem(AUDIT_KEY) || '[]');
  } catch (e) {
    logs = [];
  }
  if (!logs.length) logs = AUDIT_LOG_SEED.slice();
  const tbody = document.getElementById('audit-log-body');
  const countEl = document.getElementById('audit-log-count');
  if (!tbody) return;
  tbody.innerHTML = logs
    .map((l) => {
      const resource = l.resource || (/模板/.test(l.detail || '') ? '模板' : '合同');
      return (
        '<tr data-action-text="' +
        (l.action || '') +
        '"><td>' +
        (l.time || '—') +
        '</td><td>' +
        (l.operator || '—') +
        '</td><td>' +
        auditActionTag(l.action) +
        '</td><td>' +
        resource +
        '</td><td>' +
        (l.target || '—') +
        '</td><td>192.168.1.' +
        (10 + (l.id % 200)) +
        '</td><td><span class="tag tag-green">成功</span></td></tr>'
      );
    })
    .join('');
  if (countEl) countEl.textContent = '(共 ' + logs.length + ' 条)';
}

function filterAuditLog() {
  const page = document.getElementById('page-audit');
  if (!page) return;
  const q = (document.getElementById('audit-search')?.value || '').toLowerCase().trim();
  const actionKey = document.getElementById('audit-action-filter')?.value || '';
  const actionMap = {
    create: '创建',
    update: '修改',
    delete: '删除',
    approve: '审批',
  };
  const actionNeedle = actionMap[actionKey] || '';
  const rows = page.querySelectorAll('#audit-log-body tr');
  let visible = 0;
  rows.forEach((row) => {
    const text = row.textContent.toLowerCase();
    const actionText = row.getAttribute('data-action-text') || '';
    const matchQ = !q || text.includes(q);
    const matchA = !actionNeedle || actionText.includes(actionNeedle);
    const show = matchQ && matchA;
    row.style.display = show ? '' : 'none';
    if (show) visible += 1;
  });
  showToast('筛选完成：显示 ' + visible + ' / ' + rows.length + ' 条');
}

function filterMessages() {
  const typeFilter = document.getElementById('msg-type-filter').value;
  const statusFilter = document.getElementById('msg-status-filter').value;
  
  const items = document.querySelectorAll('#page-messages .msg-item');
  let visible = 0;
  
  items.forEach(item => {
    const itemType = item.getAttribute('data-type');
    const isUnread = item.getAttribute('data-unread') === 'true';
    
    let matchType = !typeFilter || itemType === typeFilter;
    let matchStatus = !statusFilter || (statusFilter === 'unread' && isUnread) || (statusFilter === 'read' && !isUnread);
    
    if (matchType && matchStatus) {
      item.style.display = '';
      visible++;
    } else {
      item.style.display = 'none';
    }
  });
}

function updateMessageBadge() {
  const items = document.querySelectorAll('#page-messages .msg-item');
  let unreadCount = 0;
  items.forEach(item => {
    if (item.getAttribute('data-unread') === 'true') unreadCount++;
  });
  
  // Update sidebar badge
  const sidebarBadge = document.querySelector('.nav-item[onclick*="messages"] .badge');
  if (sidebarBadge) {
    sidebarBadge.textContent = unreadCount;
    sidebarBadge.style.display = unreadCount > 0 ? '' : 'none';
  }
  
  // Update header notif-count (merge with approval count)
  const notifCount = document.getElementById('notif-count');
  if (notifCount) {
    // notif-count shows approval count, keep it separate
  }
  
  // Update page title
  const label = document.getElementById('msg-unread-label');
  if (label) {
    label.textContent = unreadCount > 0 ? `(${unreadCount} 条未读)` : '(全部已读)';
  }
  
  // Persist
  localStorage.setItem('unread-count', unreadCount);
}



// ====== 相对方创建 ======
function createCounterparty() {
  const name = document.getElementById('add-cp-name')?.value?.trim();
  if (!name) { showToast('⚠️ 请填写相对方名称'); return; }
  hideModal('add-counterparty');
  showToast('✅ 相对方创建成功');
  const cp = {
    id: Date.now(),
    name,
    type: document.querySelector('#modal-add-counterparty select')?.value || '企业',
    credit: 'A',
    status: '正常',
    createdAt: new Date().toLocaleString('zh-CN'),
  };
  const list = JSON.parse(localStorage.getItem('counterparties')||'[]');
  list.push(cp); localStorage.setItem('counterparties', JSON.stringify(list));
  renderCounterparties();
}

// ====== 模板创建/保存 ======
function createTemplate() {
  const name = document.querySelector('#modal-template-create input[name=name]')?.value;
  if (!name?.trim()) { showToast('⚠️ 请填写模板名称'); return; }
  hideModal('template-create');
  showToast('✅ 模板创建成功');
  const tpl = {id: Date.now(), name, version: 'v1.0', status: '草稿', category: document.querySelector('#modal-template-create select')?.value||'采购'};
  const list = JSON.parse(localStorage.getItem('templates')||'[]');
  list.push(tpl); localStorage.setItem('templates', JSON.stringify(list));
  renderTemplates();
}

function saveTemplateEdit() {
  const name = document.querySelector('#modal-template-edit input[name=name]')?.value;
  if (!name?.trim()) { showToast('⚠️ 模板名称不能为空'); return; }
  hideModal('template-edit');
  showToast('✅ 模板已保存，v3.3 待审批');
  const list = JSON.parse(localStorage.getItem('templates')||'[]');
  if (list.length) { list[list.length-1].version = 'v3.3'; list[list.length-1].status = '待审批'; }
  localStorage.setItem('templates', JSON.stringify(list));
  renderTemplates();
}

// ====== 批量导入 ======
function importCounterparties() {
  hideModal('import-counterparty');
  showToast('✅ 成功导入 4 条，1 条校验失败已跳过');
  const list = JSON.parse(localStorage.getItem('counterparties')||'[]');
  for (let i=0; i<4; i++) list.push({id: Date.now()+i, name:'导入相对方'+(i+1), type:'企业', credit:'A', status:'正常', imported:true});
  localStorage.setItem('counterparties', JSON.stringify(list));
  renderCounterparties();
}

// ====== 合同删除/作废 ======

// [removed duplicate deleteContract]



// [removed duplicate voidContract]


// ====== 合同创建表单验证 ======
function validateCreateForm() {
  const name = document.getElementById('new-contract-title')?.value;
  const type = document.getElementById('new-contract-type')?.value;
  const counterparty = document.getElementById('new-contract-counterparty')?.value;
  const amount = document.getElementById('new-contract-amount')?.value;
  if (!name?.trim() || !type || !counterparty || !amount) {
    showToast('⚠️ 请填写必填项（合同名称、类型、相对方、金额）');
    return false;
  }
  if (parseFloat(amount) <= 0) {
    showToast('⚠️ 合同金额必须大于 0');
    return false;
  }
  return true;
}



// ====== 批注模式切换 ======

// [removed duplicate switchAnnotationMode]


// ====== 工作区保存 ======
function saveWorkspaceProgress() {
  const progress = {
    stage: document.querySelector('.stage-tab.active')?.dataset.stage || 'legal',
    confirmed: document.querySelectorAll('.review-panel .finding-handled').length,
    total: document.querySelectorAll('.review-panel').length,
    savedAt: new Date().toLocaleString('zh-CN')
  };
  localStorage.setItem('workspace-progress', JSON.stringify(progress));
  showToast('✅ 评审进度已保存');
}

// ====== 接受修改建议 ======
function acceptSuggestion(suggestionId) {
  showToast('✅ 修改建议已接受');
  const panel = document.querySelector('[data-suggestion-id="' + suggestionId + '"]');
  if (panel) {
    panel.classList.add('suggestion-accepted');
    const btn = panel.querySelector('.btn-outline');
    if (btn) { btn.disabled = true; btn.textContent = '已接受'; }
  }
}

// ====== 退回起草人 ======

// [removed duplicate returnToDrafter]


// ====== 高管审批通过 ======
function executiveApprove() {
  if (!confirm('确认批准此合同？批准后进入用印流程。')) return;
  showToast('✅ 合同审批通过！进入用印流程');
  document.querySelector('[data-stage=executive]').classList.add('completed');
  localStorage.setItem('contract-status', 'approved');
  setTimeout(() => {
    if (confirm('审批已通过，是否进入用印管理？')) switchPage('seal');
  }, 1500);
}

// ====== 套用标准条款 ======
function applyStandardClause(clauseId) {
  showToast('✅ 标准条款已套用');
  const clause = document.querySelector('[data-clause-id="' + clauseId + '"]');
  if (clause) {
    clause.classList.add('standard-applied');
    clause.style.borderLeftColor = 'var(--success)';
  }
}

// ====== AI自动补全 ======
function aiAutoFill() {
  showToast('🔄 AI 已自动补全质保条款');
  setTimeout(() => showToast('✅ AI 补全完成，已添加 2 条质保条款'), 1500);
}

// ====== 批量套用冲突条款 ======
function batchApplyConflictClauses() {
  showToast('✅ 全部冲突条款已套用标准模板');
  document.querySelectorAll('.conflict-clause').forEach(c => {
    c.classList.add('resolved');
    c.style.background = '#f0fdf4';
  });
}

// ====== AI补全缺失条款 ======
function aiFillMissingClauses() {
  showToast('🔄 AI 正在补全缺失条款...');
  setTimeout(() => showToast('✅ AI 已自动补全全部缺失条款'), 2000);
}

// ====== 相对方信息保存 ======
function saveCounterpartyInfo() {
  const name = document.querySelector('#page-counterparties .counterparty-detail input')?.value;
  if (!name?.trim()) { showToast('⚠️ 请填写相对方名称'); return; }
  showToast('✅ 相对方信息已保存');
  localStorage.setItem('counterparty-detail', JSON.stringify({name, updatedAt: new Date().toLocaleString('zh-CN')}));
}

// ====== 配置保存 ======
function saveConfig() {
  const config = {};
  document.querySelectorAll('#page-config input, #page-config select, #page-config textarea').forEach(el => {
    if (el.name) config[el.name] = el.value;
  });
  localStorage.setItem('system-config', JSON.stringify(config));
  showToast('✅ 配置已保存');
}

// ====== 用户状态切换 ======
function toggleUserStatus(userId) {
  const users = JSON.parse(localStorage.getItem('users')||'[]');
  const user = users.find(u => u.id === userId);
  if (user) {
    user.status = user.status === '正常' ? '已禁用' : '正常';
    localStorage.setItem('users', JSON.stringify(users));
    showToast(user.status === '正常' ? '✅ 用户已启用' : '⚠️ 用户已禁用');
    renderUsers();
  }
}

// ====== 复制风险详情 ======
function copyRiskDetail(riskId) {
  const detail = document.querySelector('#modal-risk-detail .risk-detail-content')?.textContent || '';
  navigator.clipboard?.writeText(detail).then(() => {
    showToast('📋 风险详情已复制到剪贴板');
  }).catch(() => {
    showToast('⚠️ 复制失败，请手动复制');
  });
}

// ====== 批量接受AI建议 ======
function batchAcceptAllSuggestions() {
  const panels = document.querySelectorAll('.review-panel');
  let count = 0;
  panels.forEach(p => {
    if (!p.classList.contains('finding-handled')) {
      p.classList.add('finding-handled');
      count++;
    }
  });
  showToast('✅ 全部 ' + count + ' 条 AI 建议已接受');
  updateWorkspaceProgress();
}

// ====== 内联编辑保存 ======
function saveInlineEdit() {
  const textarea = event.target.closest('.inline-edit')?.querySelector('textarea');
  if (textarea) {
    localStorage.setItem('inline-edit-' + Date.now(), textarea.value);
    showToast('✅ 修改已保存');
    textarea.closest('.inline-edit')?.classList.remove('editing');
  }
}

// ====== 高管驳回重拟 ======
function rejectRedraft() {
  if (!confirm('确认驳回重拟？起草人将收到通知并重新起草。')) return;
  showToast('❌ 合同已驳回重拟，起草人将收到通知');
  localStorage.setItem('contract-status', 'redraft');
  setTimeout(() => switchPage('approvals'), 1000);
}

// ====== AI重新审查 ======
function aiReReview() {
  showToast('🔄 AI 正在重新审查合同...');
  setTimeout(() => {
    showToast('✅ 重新审查完成，风险评分已更新');
    const scoreEl = document.querySelector('.risk-score-value');
    if (scoreEl) scoreEl.textContent = Math.floor(Math.random()*30+40);
  }, 3000);
}


// [removed duplicate executiveApprove]


// ====== 条款比对函数 ======
function filterCompare(status) {
  document.querySelectorAll('#page-clause-compare .compare-nav-btn').forEach((b) => {
    b.classList.remove('active');
    const onclick = b.getAttribute('onclick') || '';
    if (onclick.includes("'" + status + "'") || onclick.includes('"' + status + '"')) {
      b.classList.add('active');
    }
  });
  const panes = ['compare-left', 'compare-right'];
  panes.forEach(paneId => {
    document.querySelectorAll('#' + paneId + ' .compare-clause').forEach(clause => {
      if (status === 'all') clause.style.display = '';
      else clause.style.display = clause.dataset.status === status ? '' : 'none';
    });
  });
}

function applyTemplateClause(btn) {
  const clause = btn.closest('.compare-clause');
  clause.classList.remove('conflict');
  clause.classList.add('match');
  clause.querySelector('.compare-badge').textContent = '✓ 已套用';
  clause.querySelector('.compare-badge').className = 'compare-badge match';
  clause.querySelector('.clause-action-bar').innerHTML = '<span style="font-size:11px;color:var(--success)">✅ 已套用标准条款</span>';
  showToast('标准条款已套用');
}

function aiFillClause(btn) {
  const clause = btn.closest('.compare-clause');
  clause.classList.remove('missing');
  clause.classList.add('match');
  clause.querySelector('.compare-badge').textContent = '✓ 已补全';
  clause.querySelector('.compare-badge').className = 'compare-badge match';
  // Also update the right pane's missing entry
  const rightMissing = document.querySelector('#compare-right .compare-clause.missing');
  if (rightMissing) {
    rightMissing.classList.remove('missing');
    rightMissing.classList.add('match');
    const badge = rightMissing.querySelector('.compare-badge');
    if (badge) { badge.textContent = '✓ 已补全'; badge.className = 'compare-badge match'; }
  }
  showToast('AI 已自动补全质保条款');
}

function batchApplyTemplate() {
  if (!confirm('将全部冲突条款替换为标准模板条款，确认？')) return;
  document.querySelectorAll('#page-clause-compare .compare-clause.conflict').forEach(clause => {
    clause.classList.remove('conflict');
    clause.classList.add('match');
    const badge = clause.querySelector('.compare-badge');
    if (badge) { badge.textContent = '✓ 已套用'; badge.className = 'compare-badge match'; }
    const bar = clause.querySelector('.clause-action-bar');
    if (bar) bar.innerHTML = '<span style="font-size:11px;color:var(--success)">✅ 已批量套用</span>';
  });
  showToast('全部冲突条款已套用标准模板');
}

function aiBatchComplete() {
  document.querySelectorAll('#page-clause-compare .compare-clause.missing').forEach(clause => {
    clause.classList.remove('missing');
    clause.classList.add('match');
    const badge = clause.querySelector('.compare-badge');
    if (badge) { badge.textContent = '✓ 已补全'; badge.className = 'compare-badge match'; }
  });
  showToast('AI 已自动补全全部缺失条款');
}

// ====== 相对方编辑 ======
function openCounterpartyEdit() {
  document.getElementById('edit-cnt-name').value = '华为技术有限公司';
  document.getElementById('edit-cnt-credit').value = '91440300279525188X';
  document.getElementById('edit-cnt-industry').value = '信息技术';
  document.getElementById('edit-cnt-rating').value = 'AAA';
  document.getElementById('edit-cnt-contact').value = '李经理';
  document.getElementById('edit-cnt-phone').value = '13800138000';
  showModal('edit-counterparty');
}
function saveCounterpartyEdit() {
  hideModal('edit-counterparty');
  showToast('相对方信息已保存');
}

// ====== 配置编辑 ======
function openConfigEdit() {
  document.getElementById('config-modal-title').textContent = '编辑配置';
  document.getElementById('edit-config-name').value = '金额阈值-标准流程';
  document.getElementById('edit-config-value').value = '500000';
  document.getElementById('edit-config-desc').value = '超过50万触发标准审批流程';
  document.getElementById('edit-config-status').value = '启用';
  showModal('edit-config');
}
function openConfigAdd() {
  document.getElementById('config-modal-title').textContent = '新增配置';
  document.getElementById('edit-config-name').value = '';
  document.getElementById('edit-config-value').value = '';
  document.getElementById('edit-config-desc').value = '';
  document.getElementById('edit-config-status').value = '启用';
  showModal('edit-config');
}
function saveConfigEdit() {
  hideModal('edit-config');
  const val = parseFloat(document.getElementById('edit-config-value')?.value);
  if (!Number.isNaN(val)) {
    try {
      const existing = JSON.parse(localStorage.getItem('flow_thresholds') || '{}');
      existing.purchase = { ...(existing.purchase || {}), simpleMax: val };
      localStorage.setItem('flow_thresholds', JSON.stringify(existing));
    } catch (e) {
      showToast('配置保存失败：' + e.message);
      return;
    }
  }
  showToast('配置已保存，新建合同将按新阈值匹配流程');
}

// ====== 归档详情 ======
function showArchiveDetail() {
  showModal('archive-detail');
}

// ====== 用印详情 ======
function showSealDetail() {
  showModal('seal-detail');
}
function confirmSeal() {
  hideModal('seal-detail');
  showToast('用印已确认，合同进入归档流程');
}

// ====== 用户管理 ======
function openUserEdit() {
  document.getElementById('user-modal-title').textContent = '编辑用户';
  document.getElementById('edit-user-name').value = '张三';
  document.getElementById('edit-user-empid').value = 'EMP001';
  document.getElementById('edit-user-dept').value = '采购部';
  document.getElementById('edit-user-role').value = '起草人';
  document.getElementById('edit-user-phone').value = '13800138000';
  document.getElementById('edit-user-status').value = '正常';
  showModal('edit-user');
}
function openUserAdd() {
  document.getElementById('user-modal-title').textContent = '新增用户';
  document.getElementById('edit-user-name').value = '';
  document.getElementById('edit-user-empid').value = '';
  document.getElementById('edit-user-dept').value = '采购部';
  document.getElementById('edit-user-role').value = '起草人';
  document.getElementById('edit-user-phone').value = '';
  document.getElementById('edit-user-status').value = '正常';
  showModal('edit-user');
}
function saveUserEdit() {
  hideModal('edit-user');
  showToast('用户信息已保存');
}

// [removed duplicate toggleUserStatus]


// ====== 修订记录 ======
function showRevisionRecord() {
  showModal('revision-record');
}

function persistState() {
  state.contracts = contracts.map(normalizeContract);
  state.workspaceConfirmed = workspaceConfirmed;
  const nc = document.getElementById('notif-count');
  state.approvalCount = nc ? parseInt(nc.textContent, 10) || 0 : 0;
  if (state.strictRbac === undefined) state.strictRbac = false;
  saveState(state);
}

// 角色切换（roleConfig 见 01-data.js；严格权限时隐藏无权限菜单）
function switchRole(role) {
  state.role = role;
  persistState();
  document.querySelector('.sidebar-footer .user-name').textContent = roleConfig[role].name;
  document.querySelector('.sidebar-footer .user-role').textContent = roleConfig[role].dept + ' · ' + roleConfig[role].title;

  const visible = roleConfig[role].visiblePages || [];
  const strict = !!state.strictRbac;
  let restrictedCount = 0;
  document.querySelectorAll('.nav-item').forEach((item) => {
    const onclick = item.getAttribute('onclick') || '';
    const pageMatch = onclick.match(/switchPage\('([\w-]+)'\)/);
    const page = pageMatch ? pageMatch[1] : null;
    const allowed = !page || visible.includes(page);
    item.classList.remove('nav-restricted');
    item.removeAttribute('title');
    if (!allowed) {
      restrictedCount++;
      if (strict) {
        item.style.display = 'none';
      } else {
        item.style.display = '';
        item.classList.add('nav-restricted');
        item.setAttribute('title', '正式环境：当前角色无此菜单（原型可点击预览）');
      }
    } else {
      item.style.display = '';
    }
  });
  document.querySelectorAll('.nav-group').forEach((group) => {
    const items = group.querySelectorAll('.nav-item');
    const anyVisible = Array.from(items).some((el) => el.style.display !== 'none');
    group.style.display = strict && !anyVisible ? 'none' : '';
  });

  const createBtn = document.querySelector('.header-btn[onclick*="create"]');
  if (createBtn) {
    if (strict && !visible.includes('create')) {
      createBtn.style.display = 'none';
    } else {
      createBtn.style.display = '';
      if (!visible.includes('create')) {
        createBtn.classList.add('header-restricted');
        createBtn.title = '正式环境：当前角色不可新建合同';
      } else {
        createBtn.classList.remove('header-restricted');
        createBtn.removeAttribute('title');
      }
    }
  }

  const rbacToggle = document.getElementById('strict-rbac-toggle');
  if (rbacToggle) rbacToggle.checked = strict;

  const msg = strict
    ? '已切换为「' + roleConfig[role].title + '」· 严格权限（隐藏 ' + restrictedCount + ' 项菜单）'
    : '已切换为「' + roleConfig[role].title + '」· 原型展示全部菜单（' + restrictedCount + ' 项正式环境不可见）';
  showToast(msg);
}


// 更新看板统计数据
function updateDashboardStats() {
  const total = contracts.length;
  const pending = contracts.filter(c => c.status === 'pending').length;
  const executing = contracts.filter(c => c.status === 'executing' || c.status === 'approved' || c.status === 'signed').length;
  const expiring = getExpiringContracts().length + getOverdueContracts().length;
  
  const setStat = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };
  setStat('dash-stat-total', total);
  setStat('dash-stat-pending', pending);
  setStat('dash-stat-executing', executing);
  setStat('dash-stat-expiring', expiring);
  const statsGrid = document.querySelector('#page-dashboard .stats-grid');
  if (statsGrid && !document.getElementById('dash-stat-total')) {
    const cards = statsGrid.querySelectorAll('.stat-card .value');
    if (cards[0]) cards[0].textContent = total;
    if (cards[1]) cards[1].textContent = pending;
    if (cards[2]) cards[2].textContent = executing;
    if (cards[3]) cards[3].textContent = expiring;
  }
}

// ====== SLA 倒计时 ======
const slaConfig = [
  { el: 'sla-r1-1', deadlineMin: 18, tagColors: 'tag-yellow' },  // 法务评审 24h SLO
  { el: 'sla-r1-2', deadlineMin: 22, tagColors: 'tag-green' },    // 财务评审 24h SLO
  { el: 'sla-r1-3', deadlineMin: 36, tagColors: 'tag-yellow' },   // 高管审批 48h SLO
];

function updateSLADisplay() {
  slaConfig.forEach(cfg => {
    const el = document.getElementById(cfg.el);
    if (!el) return;
    cfg.deadlineMin = Math.max(0, cfg.deadlineMin - 0.5); // 每30秒减0.5分钟
    const h = Math.floor(cfg.deadlineMin / 60);
    const m = Math.round(cfg.deadlineMin % 60);
    let tagClass = 'tag-green';
    let timeText;
    if (cfg.deadlineMin <= 0) {
      timeText = '已超时';
      tagClass = 'tag-red';
    } else if (cfg.deadlineMin < 120) {
      timeText = h > 0 ? `剩余 ${h}h${m}m` : `剩余 ${m}m`;
      tagClass = 'tag-red';
    } else if (cfg.deadlineMin < 360) {
      timeText = `剩余 ${h}h`;
      tagClass = 'tag-yellow';
    } else {
      timeText = `剩余 ${h}h`;
      tagClass = 'tag-green';
    }
    el.textContent = '时效：' + timeText;
    el.className = 'tag ' + tagClass;
    // 超时时闪烁
    if (cfg.deadlineMin <= 0 && cfg.deadlineMin > -2) {
      el.style.animation = 'pulse 1s infinite';
    }
  });
}


function openRiskDetail(panelId) {
  const detail = {
    'panel-3-1': {
      original: '甲方在合同签订后 5 个工作日内支付合同总额的 40% 作为预付款。',
      diagnosis: '预付款比例 40% 显著高于公司标准（≤30%）和行业基准（平均 25%）。触发条件：合同金额 ≥ 500,000 元且预付款 >30%。',
      riskType: 'CUAD-07 付款条件风险 | 风险等级：中风险 | 置信度：高（88%）',
      legal: '《内部财务管理制度》第 12 条：预付款比例原则上不超过合同总额的 30%。若供应商要求高于此比例，需经财务总监审批。',
      before: '甲方支付合同总额的 40% 作为预付款。',
      after: '甲方支付合同总额的 30% 作为预付款，剩余款项在验收合格后 30 日内支付。',
      negotiation: '"根据我司财务管理制度，标准预付款比例为 30%。考虑到贵司的付款周期要求，我们建议将预付款调整为 30%，剩余 70% 在验收合格后 30 日内支付。这样既保障了贵司的现金流，也符合我们的内控要求。"',
      benchmark: '📊 行业基准：预付款比例平均 25%（范围 20%-30%）<br>📊 偏离度：40% vs 25% = <span style="color:var(--danger);font-weight:600">+60% 偏离</span><br>📊 历史合同：近 12 个月平均预付款 28%'
    },
    'panel-4-1': {
      original: '乙方未按约定时间交付，每逾期一日，按合同总额的 0.5% 支付违约金。',
      diagnosis: '违约金 0.5%/日（年化 182.5%）显著高于司法实践标准（0.05%/日）。触发条件：单日违约金 > 0.1%。',
      riskType: 'CUAD-12 违约金风险 | 风险等级：高风险 | 置信度：高（94%）',
      legal: '《民法典》第 585 条：约定的违约金过分高于造成的损失的，人民法院可以根据当事人的请求予以适当减少。司法实践中，日违约金通常不超过 0.05%。',
      before: '每逾期一日，按合同总额的 0.5% 支付违约金。',
      after: '每逾期一日，按合同总额的 0.05% 支付违约金，累计不超过合同总额的 5%。',
      negotiation: '"我们理解贵司对交付时间的关注。根据《民法典》第 585 条和司法实践，日违约金 0.5% 可能被法院认定为过高而调减。建议调整为 0.05%/日并设上限 5%，这样既保障了履约约束力，也确保了条款的法律可执行性。"',
      benchmark: '📊 行业基准：日违约金 0.03%-0.05%（上限 5%-10%）<br>📊 偏离度：0.5% vs 0.05% = <span style="color:var(--danger);font-weight:600">10倍偏离</span><br>📊 司法实践：法院通常支持 ≤0.05%/日'
    },
    'panel-4-2': {
      original: '乙方违约需赔偿甲方一切损失，包括但不限于直接损失、间接损失、利润损失等。',
      diagnosis: '"赔偿一切损失" + "包括间接损失" 构成无限责任。触发条件：赔偿条款包含"一切""全部""间接损失"等无限制表述。',
      riskType: 'CUAD-13 赔偿上限风险 | 风险等级：高风险 | 置信度：高（92%）',
      legal: '《民法典》第 584 条：损失赔偿额不得超过违约一方订立合同时预见到或应当预见到的因违约可能造成的损失。无限责任条款可能被认定为显失公平。',
      before: '乙方违约需赔偿甲方一切损失，包括但不限于直接损失、间接损失、利润损失等。',
      after: '乙方违约需赔偿甲方直接损失，赔偿总额不超过合同总额的 30%。',
      negotiation: '"为明确双方责任边界，建议将赔偿范围限定为直接损失，并设上限为合同总额的 30%。这符合《民法典》第 584 条的预见性原则，也是行业惯例（通常 20%-50%）。这样可以避免未来争议，促进合作。"',
      benchmark: '📊 行业基准：赔偿上限 20%-50% 合同额（平均 30%）<br>📊 偏离度：无上限 vs 30% = <span style="color:var(--danger);font-weight:600">无限偏离</span><br>📊 司法实践：法院可能以显失公平为由调整'
    }
  };
  const d = detail[panelId] || detail['panel-3-1'];
  document.getElementById('rd-original').textContent = d.original;
  document.getElementById('rd-diagnosis').textContent = d.diagnosis;
  document.getElementById('rd-risk-type').innerHTML = d.riskType;
  document.getElementById('rd-legal').textContent = d.legal;
  document.getElementById('rd-before').textContent = d.before;
  document.getElementById('rd-after').textContent = d.after;
  document.getElementById('rd-negotiation').textContent = d.negotiation;
  document.getElementById('rd-benchmark').innerHTML = d.benchmark;
  document.getElementById('risk-detail-modal').classList.add('show');
}

function copyRiskDetail() {
  const original = document.getElementById('rd-original').textContent;
  const diagnosis = document.getElementById('rd-diagnosis').textContent;
  const legal = document.getElementById('rd-legal').textContent;
  const before = document.getElementById('rd-before').textContent;
  const after = document.getElementById('rd-after').textContent;
  const negotiation = document.getElementById('rd-negotiation').textContent;
  const text = `【原文】${original}\n\n【问题诊断】${diagnosis}\n\n【法律依据】${legal}\n\n【修改建议】\n原文：${before}\n建议：${after}\n\n【谈判话术】${negotiation}`;
  navigator.clipboard && navigator.clipboard.writeText(text);
  showToast('风险详情已复制到剪贴板');
}
function closeRiskDetail() {
  document.getElementById('risk-detail-modal').classList.remove('show');
}

// ====== 批量接受/驳回重拟 ======
function batchAcceptAll() {
  if (!confirm('将一键接受全部 AI 修改建议，确认？')) return;
  document.querySelectorAll('.review-panel').forEach(p => {
    const status = p.querySelector('.finding-status');
    if (status && !status.textContent.includes('已确认') && !status.textContent.includes('已忽略')) {
      confirmFinding(null, p.id);
    }
  });
  showToast('全部 AI 建议已接受');
}

// ====== 自行修改（内联编辑） ======
function enableInlineEdit(btn) {
  const card = btn.closest('[style*="border-radius:8px"]');
  const textEl = card.querySelector('[style*="line-height:2"]');
  if (!textEl) return;
  const original = textEl.innerHTML;
  // Replace with editable textarea
  const plainText = textEl.textContent.trim();
  const ta = document.createElement('textarea');
  ta.className = 'form-textarea';
  ta.style.cssText = 'width:100%;min-height:60px;font-size:13px;line-height:2;margin-top:8px';
  ta.value = plainText;
  textEl.style.display = 'none';
  textEl.parentNode.insertBefore(ta, textEl.nextSibling);
  btn.textContent = '✓ 确认修改';
  btn.className = 'btn btn-success btn-sm';
  btn.setAttribute('onclick', `saveInlineEdit(this, '${card.dataset.clause || ""}')`);
  btn.dataset.original = original;
  btn.dataset.textarea = 'ta';
  ta.focus();
}

function saveInlineEdit(btn) {
  const card = btn.closest('[style*="border-radius:8px"]');
  const ta = card.querySelector('textarea');
  const textEl = card.querySelector('[style*="line-height:2"]');
  if (ta && textEl) {
    textEl.innerHTML = ta.value.replace(/\n/g, '<br>');
    textEl.style.display = '';
    ta.remove();
  }
  btn.textContent = '✓ 已修改';
  btn.className = 'btn btn-success btn-sm';
  btn.disabled = true;
  showToast('修改已保存');
}

// ====== 文件下载 ======
function downloadFile(btn) {
  const fileName = btn.closest('div').textContent.trim().split('·')[0].trim();
  showToast(`📥 正在下载: ${fileName}`);
  setTimeout(() => showToast(`✅ ${fileName} 下载完成`), 1500);
}


// [removed duplicate rejectRedraft]


// ====== 审核报告生成 ======
function showReportModal() {
  document.getElementById('report-template-modal').classList.add('show');
}
function closeReportModal() {
  document.getElementById('report-template-modal').classList.remove('show');
}
function generateReport(type) {
  const names = { brief: '精简版', legal: '法务完整版', audit: '合规审计版' };
  closeReportModal();
  showToast(`正在生成${names[type]}审核报告...`);
  setTimeout(() => {
    showToast(`✅ ${names[type]}审核报告已生成，PDF 下载中`);
  }, 1500);
}

function shareReport(to) {
  const names = { legal: '法务部', finance: '财务部', executive: '高管' };
  showToast(`审核报告已发送至${names[to]}`);
}

function reReview() {
  showToast('🔄 AI 正在重新审查合同...');
  setTimeout(() => {
    showToast('✅ 重新审查完成，风险评分已更新');
  }, 2000);
}

// ====== 审查报告筛选（15 标签 + CUAD + 等级） ======
function initAiReviewLabelFilter() {
  const sel = document.getElementById('review-risk-label');
  if (!sel || typeof AI_RISK_LABELS === 'undefined') return;
  if (sel.dataset.populated !== '1') {
    AI_RISK_LABELS.forEach((label) => {
      const opt = document.createElement('option');
      opt.value = label.id;
      opt.textContent = `${label.id} ${label.name}`;
      sel.appendChild(opt);
    });
    sel.dataset.populated = '1';
  }
  resetReviewFilter();
}

function filterReviewReport() {
  const labelId = document.getElementById('review-risk-label')?.value || '';
  const level = document.getElementById('review-risk-level')?.value || '';
  const type = document.getElementById('review-risk-type')?.value || '';

  const items = document.querySelectorAll('#page-ai-review .risk-item');
  let visible = 0;

  const typeMap = {
    payment: ['付款', '预付款', '支付'],
    penalty: ['违约金', '逾期'],
    indemnity: ['赔偿', '上限', '责任'],
    jurisdiction: ['管辖', '法院', '异地'],
    confidentiality: ['保密'],
    termination: ['终止', '解除'],
    warranty: ['质保', '保修'],
  };

  items.forEach((item) => {
    const itemLevel = item.classList.contains('high')
      ? 'high'
      : item.classList.contains('medium')
        ? 'medium'
        : 'low';
    const itemText = item.textContent;

    const matchLabel = !labelId || item.dataset.labelId === labelId;
    const matchLevel = !level || itemLevel === level;

    let matchType = !type;
    if (type) {
      if (item.dataset.cuadType) {
        matchType = item.dataset.cuadType === type;
      } else if (typeMap[type]) {
        matchType = typeMap[type].some((keyword) => itemText.includes(keyword));
      }
    }

    if (matchLabel && matchLevel && matchType) {
      item.style.display = '';
      visible++;
    } else {
      item.style.display = 'none';
    }
  });

  const countEl = document.getElementById('review-filter-count');
  if (countEl) {
    countEl.textContent = `显示 ${visible} / ${items.length} 项`;
  }
}

function resetReviewFilter() {
  const labelSel = document.getElementById('review-risk-label');
  const levelSel = document.getElementById('review-risk-level');
  const typeSel = document.getElementById('review-risk-type');
  if (labelSel) labelSel.value = '';
  if (levelSel) levelSel.value = '';
  if (typeSel) typeSel.value = '';

  const items = document.querySelectorAll('#page-ai-review .risk-item');
  items.forEach((item) => {
    item.style.display = '';
  });

  const countEl = document.getElementById('review-filter-count');
  if (countEl) {
    countEl.textContent = `显示 ${items.length} / ${items.length} 项`;
  }
}


function loadReviewHistory(contractNo) {
  document.querySelectorAll('.review-history-contract-item').forEach(el => {
    el.classList.remove('active');
    el.style.background = '';
    el.style.borderColor = 'var(--gray-200)';
  });
  const activeItem =
    (typeof event !== 'undefined' && event?.target?.closest?.('.review-history-contract-item')) ||
    document.querySelector(`.review-history-contract-item[onclick*="${contractNo}"]`);
  if (activeItem) {
    activeItem.classList.add('active');
    activeItem.style.background = 'rgba(37,99,235,0.05)';
    activeItem.style.borderColor = 'var(--primary-light)';
  }
  showToast('📜 已加载 ' + contractNo + ' 评审历史');
  // Load from localStorage
  const history = JSON.parse(localStorage.getItem('review-history-' + contractNo) || 'null');
  if (history) {
    document.getElementById('review-history-detail').innerHTML = history.html;
  }
}

function exportReviewHistory() {
  showToast('📄 评审报告已导出');
  const data = "评审序号,版本,开始时间,结束时间,耗时,AI风险,法务结论,财务结论,高管结论\n1,v1,2024-01-10 09:00,2024-01-11 14:30,29.5h,6项,有条件通过,-,退回\n2,v2,2024-01-12 09:00,2024-01-13 16:00,31h,4项,有条件通过,有条件通过,-\n3,v3,2024-01-15 09:00,2024-01-15 16:30,7.5h,2项,通过,通过,批准";
  const blob = new Blob([data], {type:'text/csv'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = 'review-history-CTR-20240115-0001.csv'; a.click(); URL.revokeObjectURL(a.href);
}

// ====== 草稿管理 ======
autoSaveTimer = null;

function loadDraft() {
  const draftStr = localStorage.getItem('contract-draft');
  if (!draftStr) return null;
  try {
    return JSON.parse(draftStr);
  } catch(e) {
    return null;
  }
}


// [removed duplicate restoreDraft]


function clearDraft() {
  localStorage.removeItem('contract-draft');
  const draftBadge = document.getElementById('draft-badge');
  if (draftBadge) draftBadge.style.display = 'none';
}

// 起草自动保存见 00-core.js startDraftAutoSave


// ====== 历史合同引用（modal 方式）======
function showHistorySelector() {
  showModal('history-selector');
  
  // Populate history list from localStorage
  const allContracts = (typeof contracts !== 'undefined' ? contracts : []).slice();
  const defaults = [
    { no: 'CTR-20240115-0001', title: '服务器采购合同', type: 'purchase', amount: '2500000', counterparty: '华为技术', version: 3, status: '已通过', createdAt: '2024-01-15', startDate: '2024-01-20', endDate: '2025-01-20', content: '第一条 采购内容\n甲方向乙方采购服务器设备一批，包含机架式服务器 50 台、存储阵列 5 套。\n\n第二条 合同金额\n合同总金额为人民币 2,500,000 元（含税），税率 13%。\n\n第三条 付款条件\n预付款 30%，验收合格后支付 70%。\n\n第四条 违约责任\n乙方逾期交付，每日按合同总额 0.05% 支付违约金。\n\n第五条 质保条款\n乙方提供 36 个月质量保证。' },
    { no: 'CTR-20240111-0008', title: '云服务年框协议', type: 'purchase', amount: '850000', counterparty: '阿里云', version: 2, status: '执行中', createdAt: '2024-01-11', startDate: '2024-02-01', endDate: '2025-01-31', content: '第一条 服务内容\n乙方向甲方提供云计算服务，包括但不限于 ECS、OSS、CDN 等。\n\n第二条 合同金额\n年度框架金额为人民币 850,000 元。\n\n第三条 付款方式\n按季度结算，每季度初支付当季费用的 50%，季度末结清。\n\n第四条 服务水平\n乙方保证服务可用性不低于 99.95%。' },
    { no: 'CTR-20240108-0005', title: '年度采购框架', type: 'purchase', amount: '5000000', counterparty: '联想集团', version: 5, status: '已归档', createdAt: '2024-01-08', startDate: '2024-01-15', endDate: '2024-12-31', content: '第一条 合作内容\n本协议为年度采购框架协议，适用于甲方向乙方采购办公设备及IT产品的所有订单。\n\n第二条 框架金额\n年度框架总额不超过人民币 5,000,000 元。\n\n第三条 定价机制\n按附件《产品价格清单》执行，价格有效期为 12 个月。\n\n第四条 违约责任\n双方应严格履行本协议，违约方需赔偿守约方全部直接损失。' },
    { no: 'CTR-20240105-0012', title: '办公区装修合同', type: 'purchase', amount: '320000', counterparty: '中建装饰', version: 1, status: '已通过', createdAt: '2024-01-05', startDate: '2024-02-01', endDate: '2024-04-30', content: '第一条 工程范围\n乙方承接甲方办公区装饰装修工程，总面积 1,200 平方米。\n\n第二条 合同金额\n工程总价为人民币 320,000 元。\n\n第三条 工期\n工期为 90 日历天，自开工之日起算。\n\n第四条 质量保证\n工程质量符合国家相关标准，质保期 24 个月。' },
    { no: 'CTR-20240103-0003', title: '网络安全服务合同', type: 'purchase', amount: '180000', counterparty: '奇安信', version: 2, status: '执行中', createdAt: '2024-01-03', startDate: '2024-01-10', endDate: '2025-01-09', content: '第一条 服务内容\n乙方为甲方提供网络安全监测、漏洞扫描、应急响应等安全服务。\n\n第二条 合同金额\n年度服务费为人民币 180,000 元。\n\n第三条 服务级别\n提供 7×24 小时安全监控，重大安全事件 30 分钟内响应。\n\n第四条 保密条款\n乙方对服务过程中获取的甲方信息系统数据负有保密义务。' },
  ];
  
  // Merge: defaults + localStorage contracts (avoid duplicates by no)
  const seen = new Set(defaults.map(c => c.no));
  const merged = [...defaults, ...allContracts.filter(c => !seen.has(c.no))];
  
  const listContent = document.getElementById('history-list-content');
  if (!listContent) return;
  
  if (merged.length === 0) {
    listContent.innerHTML = '<div style="text-align:center;padding:30px;color:var(--gray-400)"><div style="font-size:32px;margin-bottom:8px">📭</div><div>暂无历史合同</div><div style="font-size:11px;margin-top:4px">先创建一份合同后即可引用</div></div>';
  } else {
    const statusColors = { '已通过': 'tag-green', '执行中': 'tag-blue', '已归档': 'tag-gray', '待审批': 'tag-yellow', '已作废': 'tag-red' };
    listContent.innerHTML = merged.map(c => `
      <div class="history-option" onclick="selectHistoryContract('${c.no}')" style="padding:12px;border:1px solid var(--gray-200);border-radius:8px;margin-bottom:8px;cursor:pointer;transition:all 0.2s" onmouseover="this.style.borderColor='var(--primary)';this.style.background='#eff6ff'" onmouseout="this.style.borderColor='var(--gray-200)';this.style.background=''">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
          <span style="font-size:13px;font-weight:600">${c.no} ${c.title}</span>
          <span class="tag ${statusColors[c.status] || 'tag-gray'}" style="font-size:10px">${c.status || '已通过'}</span>
        </div>
        <div style="font-size:12px;color:var(--gray-500)">金额：¥${parseFloat(c.amount || 0).toLocaleString()} · 相对方：${c.counterparty || '-'} · v${c.version || 1} · ${c.createdAt || ''}</div>
      </div>
    `).join('');
  }
}

function filterHistoryContracts() {
  const query = document.getElementById('history-search-input').value.toLowerCase();
  document.querySelectorAll('.history-option').forEach(opt => {
    const text = opt.textContent.toLowerCase();
    opt.style.display = text.includes(query) ? '' : 'none';
  });
}

function selectHistoryContract(contractNo) {
  hideModal('history-selector');
  
  // 记录引用来源
  localStorage.setItem('contract-referenced-from', contractNo);
  
  // 从 localStorage 获取历史合同
  const allContracts = JSON.parse(localStorage.getItem('contracts') || '[]');
  const contract = allContracts.find(c => c.no === contractNo);
  
  if (!contract) {
    showToast('⚠️ 未找到合同 ' + contractNo);
    return;
  }
  
  // 填充表单
  document.getElementById('new-contract-title').value = contract.title + '（引用）';
  document.getElementById('new-contract-type').value = contract.type;
  document.getElementById('new-contract-counterparty').value = contract.counterparty;
  document.getElementById('new-contract-amount').value = '';
  document.getElementById('new-contract-start').value = contract.startDate || '';
  document.getElementById('new-contract-end').value = contract.endDate || '';
  document.getElementById('new-contract-content').value = '【引用自 ' + contractNo + '】\n\n' + (contract.content || '');
  
  // 锁定关键字段（类型/相对方不可修改）
  lockField('new-contract-type', 'history');
  lockField('new-contract-counterparty', 'history');
  lockField('new-contract-title', 'history');
  
  // 显示历史引用提示
  document.getElementById('history-ref-contract-no').textContent = '📄 ' + contractNo + ' · ' + contract.title + ' · ' + (contract.counterparty || '');
  document.getElementById('history-ref-note').style.display = 'block';
  
  // 更新指示器
  updateModeIndicator('history', contract.title);
  document.getElementById('mode-indicator-detail').textContent = '— 金额已清空，请根据当前业务重新填写';
  
  showToast('✅ 已引用合同 ' + contractNo + '，金额已清空请重新填写');
}

// ====== 相对方管理 ======
function showCounterpartyDropdown() {
  // Auto-populate dropdown on first focus
  filterCounterparties();
}

function hideCounterpartyDropdown() {
  setTimeout(() => {
    document.getElementById('counterparty-dropdown').style.display = 'none';
  }, 200);
}

function filterCounterparties() {
  const query = document.getElementById('new-contract-counterparty').value.toLowerCase();
  
  // Load counterparties from localStorage + defaults
  const defaults = [
    { name: '华为技术有限公司', credit: '91440300279444444X', rating: 'AAA' },
    { name: '阿里云计算有限公司', credit: '91330000MA27XN3B4X', rating: 'AAA' },
    { name: '联想集团有限公司', credit: '91110108717884349J', rating: 'AA' },
    { name: '中建装饰集团有限公司', credit: '91440300192234567X', rating: 'AA' },
    { name: '腾讯科技有限公司', credit: '91440300335432271A', rating: 'AAA' },
    { name: '百度在线网络技术有限公司', credit: '91110000717850825A', rating: 'AAA' },
  ];
  
  const stored = JSON.parse(localStorage.getItem('counterparties') || '[]');
  const all = [...defaults, ...stored.map(c => ({ name: c.name, credit: c.creditCode || '', rating: c.rating || 'A' }))];
  
  // Remove duplicates by name
  const seen = new Set();
  const unique = all.filter(c => { if (seen.has(c.name)) return false; seen.add(c.name); return true; });
  
  const filtered = query ? unique.filter(c => c.name.toLowerCase().includes(query) || (c.credit && c.credit.includes(query))) : unique;
  
  const dropdownContent = document.getElementById('counterparty-dropdown-content');
  if (!dropdownContent) return;
  
  if (filtered.length === 0) {
    dropdownContent.innerHTML = '<div style="padding:12px;text-align:center;color:var(--gray-400);font-size:12px">无匹配结果，请点击下方"新建相对方"</div>';
  } else {
    dropdownContent.innerHTML = filtered.map((c) => {
      const bl = isBlacklisted(c.name);
      return `<div class="counterparty-option" data-name="${escapeHtml(c.name)}" data-credit="${escapeHtml(c.credit)}" onclick="selectCounterparty(this.dataset.name,this.dataset.credit)" style="padding:8px 12px;cursor:pointer;border-bottom:1px solid var(--gray-100)" onmouseover="this.style.background='#eff6ff'" onmouseout="this.style.background=''">
        <div style="font-size:13px;font-weight:600">${escapeHtml(c.name)}${bl ? ' <span class="tag tag-red" style="font-size:10px">黑名单</span>' : ''}</div>
        <div style="font-size:11px;color:var(--gray-400)">${c.credit ? '信用代码：' + escapeHtml(c.credit) + ' · ' : ''}${c.rating}</div>
      </div>`;
    }).join('');
  }
  
  document.getElementById('counterparty-dropdown').style.display = 'block';
}

function selectCounterparty(name, creditCode) {
  if (isBlacklisted(name)) {
    showToast('🚫 该相对方在黑名单中，请更换或联系法务');
    const infoBl = document.getElementById('counterparty-credit-info');
    if (infoBl) {
      infoBl.style.display = 'block';
      infoBl.style.background = '#fef2f2';
      infoBl.style.color = 'var(--danger)';
      infoBl.innerHTML = '🚫 黑名单相对方，不建议签约';
    }
  }
  document.getElementById('new-contract-counterparty').value = name;
  document.getElementById('counterparty-dropdown').style.display = 'none';

  const info = document.getElementById('counterparty-credit-info');
  if (!info) return;
  info.style.display = 'block';
  if (isBlacklisted(name)) return;
  info.style.background = '#f0fdf4';
  info.style.color = 'var(--success)';
  info.innerHTML = '✅ 信用代码：' + creditCode + ' · 已验证';
  validateCreditCode(creditCode);
}

function validateCreditCode(code) {
  // 统一社会信用代码格式：18 位，由数字和大写字母组成
  const regex = /^[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}$/;
  const info = document.getElementById('counterparty-credit-info');
  
  if (!code) return true;
  
  if (regex.test(code)) {
    info.style.background = '#f0fdf4';
    info.style.color = 'var(--success)';
    info.innerHTML = '✅ 信用代码格式正确';
    return true;
  } else {
    info.style.background = '#fef2f2';
    info.style.color = 'var(--danger)';
    info.innerHTML = '❌ 信用代码格式错误（应为 18 位数字+大写字母）';
    return false;
  }
}

function showNewCounterpartyModal() {
  document.getElementById('new-counterparty-name').value = '';
  document.getElementById('new-counterparty-credit').value = '';
  document.getElementById('new-counterparty-credit-info').style.display = 'none';
  showModal('new-counterparty');
}

function saveNewCounterparty() {
  const name = document.getElementById('new-counterparty-name').value;
  const credit = document.getElementById('new-counterparty-credit').value;
  
  if (!name) {
    showToast('⚠️ 请填写相对方名称');
    return;
  }
  
  if (credit && !validateCreditCode(credit)) {
    showToast('⚠️ 信用代码格式错误');
    return;
  }
  
  // 保存到 localStorage
  const counterparties = JSON.parse(localStorage.getItem('counterparties') || '[]');
  counterparties.push({
    id: Date.now(),
    name: name,
    creditCode: credit || '',
    status: '正常',
    createdAt: new Date().toLocaleString('zh-CN')
  });
  localStorage.setItem('counterparties', JSON.stringify(counterparties));
  
  hideModal('new-counterparty');
  showToast('✅ 相对方 ' + name + ' 创建成功');
  
  // 自动选择新创建的相对方
  document.getElementById('new-contract-counterparty').value = name;
  const info = document.getElementById('counterparty-credit-info');
  info.style.display = 'block';
  info.style.background = '#f0fdf4';
  info.style.color = 'var(--success)';
  info.innerHTML = '✅ ' + (credit ? '信用代码：' + credit : '新创建相对方');
}

function startSLATimer() {
  updateSLADisplay();
  setInterval(updateSLADisplay, 30000);
}

/* tour: maybeShowTour in 99-init.js */
