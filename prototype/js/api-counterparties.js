/**
 * 相对方 API
 */
const ApiCounterparties = {
  create: function (body) {
    return ApiClient.post('/api/v1/counterparties/', body);
  },
  blacklist: function (cpId, reason) {
    return ApiClient.post('/api/v1/counterparties/' + cpId + '/blacklist', {
      reason: reason || '违规',
    });
  },
};
