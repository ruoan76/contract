/**
 * 真实 API 联调配置 — 默认 Mock，不影响现有 147 项原型测试。
 */
(function (global) {
  /** 设为 true 时走 backend API（需先启动 uvicorn + seed_dev） */
  global.USE_REAL_API = global.USE_REAL_API === true;

  global.API_CONFIG = {
    baseUrl: global.API_BASE_URL || 'http://127.0.0.1:8000',
    password: '123456',
    roleUsers: {
      drafter: 'drafter1',
      approver: 'approver1',
      legal: 'legal1',
      finance: 'finance1',
      executive: 'executive1',
      admin: 'admin',
      archivist: 'admin',
    },
  };
})(typeof window !== 'undefined' ? window : globalThis);
