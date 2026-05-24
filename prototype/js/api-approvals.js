/**
 * 审批 API
 */
const ApiApprovals = {
  submit: function (contractId, flowType) {
    return ApiClient.post('/api/v1/approvals/submit', {
      contract_id: contractId,
      flow_type: flowType || 'standard',
    });
  },
  approve: function (flowId, action, comment) {
    return ApiClient.post('/api/v1/approvals/' + flowId + '/approve', {
      action: action || 'approve',
      comment: comment || '',
    });
  },
  pending: function () {
    return ApiClient.get('/api/v1/approvals/pending');
  },
  history: function (flowId) {
    return ApiClient.get('/api/v1/approvals/' + flowId + '/history');
  },
  approveAllStepsForContract: async function (contractId, roles) {
    const order = roles || ['approver', 'legal', 'finance', 'executive'];
    for (let i = 0; i < order.length; i++) {
      const role = order[i];
      await ApiAuth.loginAsRole(role);
      const pending = await ApiApprovals.pending();
      const items = (pending.items || []).filter(function (x) {
        return x.contract_id === contractId;
      });
      if (!items.length) continue;
      await ApiApprovals.approve(items[0].flow_id, 'approve');
    }
  },
};
