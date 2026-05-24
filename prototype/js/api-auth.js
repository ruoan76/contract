/**
 * 多角色 JWT 登录与切换。
 */
const ApiAuth = (function () {
  const _cache = {};

  async function login(username, password) {
    const pwd = password || API_CONFIG.password;
    const qs = new URLSearchParams({ username: username, password: pwd });
    const res = await fetch(API_CONFIG.baseUrl.replace(/\/$/, '') + '/api/v1/system/login?' + qs, {
      method: 'POST',
    });
    const json = await res.json();
    if (!res.ok || json.code !== 200) {
      throw new Error((json.detail || json.message || '登录失败') + '');
    }
    ApiClient.setToken(json.data.token);
    sessionStorage.setItem('api_current_user', JSON.stringify(json.data.user));
    return json.data;
  }

  async function loginAsRole(role) {
    const username = API_CONFIG.roleUsers[role];
    if (!username) throw new Error('未知角色: ' + role);
    if (_cache[role]) {
      ApiClient.setToken(_cache[role]);
      return _cache[role];
    }
    const data = await login(username);
    _cache[role] = data.token;
    return data;
  }

  function clearCache() {
    Object.keys(_cache).forEach(function (k) {
      delete _cache[k];
    });
  }

  return {
    login: login,
    loginAsRole: loginAsRole,
    clearCache: clearCache,
  };
})();
