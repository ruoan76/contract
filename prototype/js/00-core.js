/**
 * 核心：存储、Toast/模态框、合同归一化、审计日志、黑名单
 */
const STORAGE_KEY = 'contract_proto';
const AUDIT_KEY = 'contract_audit_logs';
const BLACKLIST_KEY = 'counterparty_blacklist';
const TOUR_KEY = 'contract_proto_tour_dismissed';

/** 默认黑名单（与相对方页样例一致） */
const DEFAULT_BLACKLIST = ['某某失信科技有限公司'];

let uploadedFiles = [];
let draftAutoSaveTimer = null;
let workspaceAutoSaveTimer = null;
let currentWorkspaceFlowType = 'standard';

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (e) {
    /* 忽略损坏数据 */
  }
  return null;
}

function saveState(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    showToast('⚠️ 本地存储失败');
  }
}

/** 统一合同字段，兼容 submit 与旧数据 */
function normalizeContract(raw) {
  if (!raw || typeof raw !== 'object') return raw;
  const c = { ...raw };
  c.name = c.name || c.title || '未命名合同';
  c.title = c.title || c.name;
  c.risk = c.risk || c.riskLevel || 'low';
  c.riskName = c.riskName || c.riskLevelName || ({ low: '低风险', medium: '中风险', high: '高风险' }[c.risk] || '低风险');
  c.time = c.time || c.createdAt || '';
  c.approvalStatus = c.approvalStatus || (c.status === 'pending' ? '待审批' : c.statusName || '');
  if (!c.flowType) {
    const amt = Number(c.amount) || 0;
    c.flowType = amt >= 1000000 ? 'special' : amt >= 100000 ? 'standard' : 'simple';
  }
  return c;
}

function getBlacklistNames() {
  try {
    const stored = JSON.parse(localStorage.getItem(BLACKLIST_KEY) || '[]');
    if (Array.isArray(stored) && stored.length) return stored;
  } catch (e) {
    /* 使用默认 */
  }
  return DEFAULT_BLACKLIST.slice();
}

function isBlacklisted(name) {
  if (!name) return false;
  return getBlacklistNames().some((b) => name.includes(b) || b.includes(name));
}

function addAuditLog(action, target, detail) {
  const entry = {
    id: Date.now(),
    time: new Date().toLocaleString('zh-CN'),
    action,
    target: target || '',
    detail: detail || '',
    operator: (typeof roleConfig !== 'undefined' && state?.role && roleConfig[state.role])
      ? roleConfig[state.role].name
      : '系统',
  };
  let logs = [];
  try {
    logs = JSON.parse(localStorage.getItem(AUDIT_KEY) || '[]');
  } catch (e) {
    logs = [];
  }
  logs.unshift(entry);
  localStorage.setItem(AUDIT_KEY, JSON.stringify(logs.slice(0, 200)));
}

function exportAuditLog() {
  let logs = [];
  try {
    logs = JSON.parse(localStorage.getItem(AUDIT_KEY) || '[]');
  } catch (e) {
    logs = [];
  }
  if (!logs.length) {
    showToast('📋 暂无审计日志可导出');
    return;
  }
  const header = '时间,操作,对象,详情,操作人\n';
  const rows = logs
    .map((l) =>
      [l.time, l.action, l.target, l.detail, l.operator]
        .map((v) => `"${String(v || '').replace(/"/g, '""')}"`)
        .join(',')
    )
    .join('\n');
  const blob = new Blob(['\ufeff' + header + rows], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'audit-log-' + new Date().toISOString().slice(0, 10) + '.csv';
  a.click();
  URL.revokeObjectURL(a.href);
  showToast('✅ 审计日志已导出');
}

function showToast(text) {
  const el = document.getElementById('toast');
  const textEl = document.getElementById('toast-text');
  if (!el || !textEl) return;
  textEl.textContent = text;
  el.style.display = 'block';
  el.style.background = text.includes('⚠️') || text.includes('❌') ? 'var(--danger)' : 'var(--success)';
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => {
    el.style.display = 'none';
  }, 2800);
}

function showModal(id) {
  const el = document.getElementById('modal-' + id);
  if (el) el.classList.add('show');
}

function hideModal(id) {
  const el = document.getElementById('modal-' + id);
  if (el) el.classList.remove('show');
}

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/"/g, '&quot;');
}

/** 简易流程：评审工作台仅法务 Tab（D3） */
function applyWorkspaceFlowTabs(flowType) {
  currentWorkspaceFlowType = flowType || 'standard';
  const tabs = document.querySelectorAll('#stage-tabs .stage-tab');
  tabs.forEach((tab) => {
    const stage = tab.dataset.stage;
    if (stage === 'finance' || stage === 'executive') {
      tab.style.display = currentWorkspaceFlowType === 'simple' ? 'none' : '';
    }
  });
  if (currentWorkspaceFlowType === 'simple') {
    switchStage('legal');
  }
}

function startDraftAutoSave() {
  if (draftAutoSaveTimer) clearInterval(draftAutoSaveTimer);
  draftAutoSaveTimer = setInterval(() => {
    const title = document.getElementById('new-contract-title')?.value;
    if (title) saveDraft();
  }, 300000);
}

function stopDraftAutoSave() {
  if (draftAutoSaveTimer) {
    clearInterval(draftAutoSaveTimer);
    draftAutoSaveTimer = null;
  }
}

function startWorkspaceAutoSave() {
  if (workspaceAutoSaveTimer) clearInterval(workspaceAutoSaveTimer);
  workspaceAutoSaveTimer = setInterval(() => {
    if (typeof workspaceDirty === 'undefined' || !workspaceDirty) return;
    const indicator = document.getElementById('save-indicator');
    if (!indicator) return;
    indicator.textContent = '⏳ 自动保存中...';
    indicator.className = 'save-indicator saving';
    setTimeout(() => {
      indicator.textContent = '💾 已自动保存';
      indicator.className = 'save-indicator saved';
      if (typeof workspaceDirty !== 'undefined') workspaceDirty = false;
      if (typeof persistState === 'function') persistState();
      setTimeout(() => {
        indicator.textContent = '💾 已自动保存';
        indicator.className = 'save-indicator';
      }, 2000);
    }, 500);
  }, 30000);
}

function stopWorkspaceAutoSave() {
  if (workspaceAutoSaveTimer) {
    clearInterval(workspaceAutoSaveTimer);
    workspaceAutoSaveTimer = null;
  }
}

function showTour() {
  const hint = document.getElementById('tour-hint');
  if (hint) hint.style.display = 'flex';
}

function closeTour() {
  const hint = document.getElementById('tour-hint');
  if (hint) hint.style.display = 'none';
  localStorage.setItem(TOUR_KEY, '1');
}

function maybeShowTour() {
  if (localStorage.getItem(TOUR_KEY) === '1') return;
  setTimeout(showTour, 1500);
}

function editDraftContract(no) {
  switchPage('create');
  showToast('📝 编辑草稿：' + no + '（原型示意）');
}

function renderCounterparties() {
  showToast('✅ 相对方列表已更新');
}

function renderTemplates() {
  showToast('✅ 模板列表已更新');
}

function renderUsers() {
  showToast('✅ 用户列表已更新');
}
