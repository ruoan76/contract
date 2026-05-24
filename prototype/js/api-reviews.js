/**
 * 评审 API
 */
const ApiReviews = {
  submitOpinion: function (contractId, role, action, comment) {
    return ApiClient.post('/api/v1/reviews/contracts/' + contractId + '/opinions', {
      role: role,
      action: action || 'approve',
      comment: comment || '',
    });
  },
  returnForRevision: function (contractId, role, comment) {
    return ApiClient.post('/api/v1/reviews/contracts/' + contractId + '/return', {
      role: role || 'legal',
      comment: comment || '',
    });
  },
  pending: function (role) {
    const q = role ? '?role=' + encodeURIComponent(role) : '';
    return ApiClient.get('/api/v1/reviews/pending' + q);
  },
  workspace: function (contractId) {
    return ApiClient.get('/api/v1/reviews/contracts/' + contractId);
  },
};
