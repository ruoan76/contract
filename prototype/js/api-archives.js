/**
 * 归档 API
 */
const ApiArchives = {
  archive: function (contractId, location) {
    return ApiClient.post('/api/v1/archives/' + contractId + '/archive', {
      archive_location: location || '/archive/demo',
    });
  },
};
