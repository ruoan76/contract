/**
 * HTTP 客户端 — JWT、统一响应解析。
 */
const ApiClient = (function () {
  let _token = sessionStorage.getItem('api_token') || '';

  function setToken(token) {
    _token = token || '';
    if (_token) sessionStorage.setItem('api_token', _token);
    else sessionStorage.removeItem('api_token');
  }

  function getToken() {
    return _token;
  }

  async function request(method, path, options) {
    const opts = options || {};
    const url = (API_CONFIG.baseUrl || '').replace(/\/$/, '') + path;
    const headers = Object.assign({ Accept: 'application/json' }, opts.headers || {});
    if (_token) headers.Authorization = 'Bearer ' + _token;
    if (opts.body && !(opts.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }
    const res = await fetch(url, {
      method,
      headers,
      body: opts.body
        ? opts.body instanceof FormData
          ? opts.body
          : JSON.stringify(opts.body)
        : undefined,
    });
    let data = null;
    const text = await res.text();
    try {
      data = text ? JSON.parse(text) : null;
    } catch (e) {
      data = { detail: text };
    }
    if (!res.ok) {
      const msg = (data && (data.detail || data.message)) || res.statusText;
      const err = new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
      err.status = res.status;
      err.data = data;
      throw err;
    }
    if (data && data.code !== undefined && data.code !== 200) {
      const err = new Error(data.message || 'API error');
      err.status = data.code;
      err.data = data;
      throw err;
    }
    return data && data.data !== undefined ? data.data : data;
  }

  return {
    setToken,
    getToken,
    get: function (path) {
      return request('GET', path);
    },
    post: function (path, body) {
      return request('POST', path, { body: body });
    },
    put: function (path, body) {
      return request('PUT', path, { body: body });
    },
    patch: function (path, body) {
      return request('PATCH', path, { body: body });
    },
    health: function () {
      return fetch((API_CONFIG.baseUrl || '').replace(/\/$/, '') + '/health').then(function (r) {
        return r.ok;
      });
    },
  };
})();
