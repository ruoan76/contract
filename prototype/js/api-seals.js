/**
 * 用印 API
 */
const ApiSeals = {
  apply: function (contractId, sealType) {
    return ApiClient.post('/api/v1/seals/apply', {
      contract_id: contractId,
      seal_type: sealType || '公章',
    });
  },
  approve: function (sealId, approved) {
    return ApiClient.post('/api/v1/seals/' + sealId + '/approve', {
      approved: approved !== false,
    });
  },
};
