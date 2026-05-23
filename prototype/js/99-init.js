/**
 * 应用启动
 */
(function initApp() {
  state = loadState() || {
    contracts: JSON.parse(JSON.stringify(defaultContracts)),
    workspaceConfirmed: 0,
    approvalCount: 5,
    role: 'approver',
    strictRbac: false,
  };
  if (state.strictRbac === undefined) state.strictRbac = false;
  contracts = (state.contracts || []).map(normalizeContract);
  state.contracts = contracts;
  workspaceConfirmed = state.workspaceConfirmed || 0;

  if (typeof restoreDraft === 'function') restoreDraft();
  startDraftAutoSave();

  const roleSelect = document.getElementById('role-select');
  const currentRole = state.role || 'approver';
  if (roleSelect) roleSelect.value = currentRole;
  const rbacToggle = document.getElementById('strict-rbac-toggle');
  if (rbacToggle) rbacToggle.checked = !!state.strictRbac;
  if (typeof switchRole === 'function') switchRole(currentRole);

  const notif = document.getElementById('notif-count');
  if (notif) notif.textContent = state.approvalCount || 5;

  if (typeof renderContracts === 'function') renderContracts(contracts);
  if (typeof persistState === 'function') persistState();
  if (typeof updateDashboardStats === 'function') updateDashboardStats();
  if (typeof startSLATimer === 'function') startSLATimer();
  if (typeof updateMessageBadge === 'function') updateMessageBadge();

  if (typeof initAiReviewLabelFilter === 'function') {
    initAiReviewLabelFilter();
  }

  maybeShowTour();
})();
