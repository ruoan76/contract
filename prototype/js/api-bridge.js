/**
 * 原型 ↔ API 桥接：USE_REAL_API 时挂钩角色切换与提交。
 */
(function () {
  if (typeof USE_REAL_API === 'undefined' || !USE_REAL_API) return;

  const _origSwitchRole = typeof switchRole === 'function' ? switchRole : null;

  async function switchRoleWithApi(role) {
    try {
      await ApiAuth.loginAsRole(role);
    } catch (e) {
      if (typeof showToast === 'function') {
        showToast('⚠️ API 登录失败: ' + e.message);
      }
      console.error(e);
    }
    if (_origSwitchRole) _origSwitchRole(role);
  }

  if (_origSwitchRole) {
    switchRole = function (role) {
      switchRoleWithApi(role);
    };
  }

  /** 真实 API 提交合同（供 create 页或控制台调用） */
  async function submitContractViaApi() {
    const title = document.getElementById('new-contract-title')?.value;
    const type = document.getElementById('new-contract-type')?.value;
    const counterparty = document.getElementById('new-contract-counterparty')?.value;
    const amount = parseFloat(document.getElementById('new-contract-amount')?.value || '0');
    const content = document.getElementById('new-contract-content')?.value || '';
    if (!title || !type || !counterparty || !amount) {
      showToast('⚠️ 请填写必填项');
      return null;
    }
    await ApiAuth.loginAsRole(state.role || 'drafter');
    const flowType =
      typeof resolveFlowType === 'function' ? resolveFlowType(type, amount) : amount >= 1000000 ? 'special' : amount >= 100000 ? 'standard' : 'simple';
    const created = await ApiContracts.create({
      title: title,
      contract_type: type,
      counterparty_name: counterparty,
      amount: amount,
      content: content || '合同正文',
    });
    const flow = await ApiApprovals.submit(created.id, flowType === 'special' ? 'large_amount' : flowType);
    sessionStorage.setItem('api_last_contract_id', String(created.id));
    sessionStorage.setItem('api_last_flow_id', String(flow.flow_id));
    showToast('✅ 已提交至后端 API · 合同 #' + created.id);
    return { contract: created, flow: flow };
  }

  if (typeof submitContract === 'function') {
    const _origSubmit = submitContract;
    submitContract = function () {
      submitContractViaApi().catch(function (e) {
        showToast('⚠️ API 提交失败: ' + e.message);
        console.error(e);
      });
    };
  }

  window.submitContractViaApi = submitContractViaApi;

  /** 启动时登录当前角色 */
  document.addEventListener('DOMContentLoaded', function () {
    const role = (typeof state !== 'undefined' && state.role) || 'approver';
    ApiAuth.loginAsRole(role).catch(function () {
      /* 后端未启动时静默 */
    });
  });
})();
