/**
 * AI 审查 API
 */
const ApiAi = {
  review: function (contractId) {
    return ApiClient.post('/api/v1/ai-review/review', { contract_id: contractId });
  },
};
