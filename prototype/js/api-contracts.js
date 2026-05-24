/**
 * 合同 API
 */
const ApiContracts = {
  create: function (payload) {
    return ApiClient.post('/api/v1/contracts/', payload);
  },
  get: function (id) {
    return ApiClient.get('/api/v1/contracts/' + id);
  },
  list: function (params) {
    const q = new URLSearchParams(params || {}).toString();
    return ApiClient.get('/api/v1/contracts/' + (q ? '?' + q : ''));
  },
  dashboard: function () {
    return ApiClient.get('/api/v1/contracts/dashboard');
  },
  matchFlow: function (amount) {
    return ApiClient.get('/api/v1/contracts/match-flow?amount=' + encodeURIComponent(amount));
  },
  submitRevision: function (id, body) {
    return ApiClient.post('/api/v1/contracts/' + id + '/revisions', body);
  },
};
