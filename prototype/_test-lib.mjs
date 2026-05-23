/**
 * 原型测试公共库：常量（与 01-data.js / DESIGN_STATUS 同步）、Runner、Puppeteer 辅助
 */
import puppeteer from 'puppeteer';

export const BASE = process.env.PROTO_URL || 'http://127.0.0.1:8765/index.html';
export const DELAY = Number(process.env.TEST_DELAY) || 100;

/** 20 个 pageId（17 侧栏 + 3 下钻） */
export const ALL_PAGE_IDS = [
  'dashboard', 'messages', 'create', 'contracts', 'templates',
  'ai-review', 'clause-compare', 'review-center', 'review-workspace', 'review-history',
  'approvals', 'approval-history', 'revision-workspace',
  'seal', 'archives', 'counterparties', 'config', 'users', 'audit', 'contract-detail',
];

export const NAV_PAGES = ALL_PAGE_IDS.filter(
  (id) => !['contract-detail', 'approval-history', 'revision-workspace'].includes(id),
);

export const DRILLDOWN_PAGES = ['contract-detail', 'approval-history', 'revision-workspace'];

/** 与 js/01-data.js roleConfig.visiblePages 一致 */
export const ROLE_VISIBLE = {
  drafter: ['dashboard', 'messages', 'contracts', 'create', 'templates', 'ai-review', 'archives', 'counterparties', 'revision-workspace'],
  approver: ['dashboard', 'messages', 'contracts', 'create', 'templates', 'ai-review', 'clause-compare', 'approvals', 'archives', 'review-center', 'review-workspace', 'counterparties', 'config'],
  legal: ['dashboard', 'contracts', 'ai-review', 'clause-compare', 'seal', 'archives', 'review-center', 'review-workspace', 'templates'],
  finance: ['dashboard', 'contracts', 'ai-review', 'clause-compare', 'archives', 'review-center', 'review-workspace'],
  archivist: ['dashboard', 'contracts', 'seal', 'archives'],
  admin: ['dashboard', 'messages', 'contracts', 'create', 'templates', 'ai-review', 'clause-compare', 'review-center', 'review-workspace', 'review-history', 'approvals', 'seal', 'archives', 'counterparties', 'config', 'users', 'audit'],
};

/** switchPage titles 首段（02-app.js） */
export const PAGE_TITLES = {
  dashboard: '状态看板',
  messages: '消息中心',
  create: '新建合同',
  contracts: '合同列表',
  templates: '模板管理',
  'ai-review': '审查报告',
  'clause-compare': '条款比对',
  'review-center': '评审中心',
  'review-workspace': '评审工作台',
  'review-history': '评审历史',
  approvals: '待办审批',
  'approval-history': '审批历史',
  'revision-workspace': '修订工作台',
  seal: '用印管理',
  archives: '归档台账',
  counterparties: '相对方管理',
  config: '审批配置',
  users: '用户管理',
  audit: '审计日志',
  'contract-detail': '合同详情',
};

/** 样例合同编号（defaultContracts 子集，用于数据一致性断言） */
export const SAMPLE_CONTRACT_NOS = [
  'DEMO-01', 'DEMO-03', 'DEMO-05',
  'CTR-20240115-0001', 'CTR-20240114-0003', 'CTR-20240108-0011',
];

export const MODAL_IDS = [
  'new-counterparty', 'history-selector', 'add-counterparty', 'import-counterparty',
  'edit-counterparty', 'counterparty-detail', 'approval', 'approval-detail',
  'template-create', 'template-edit', 'template-preview', 'edit-config', 'archive-detail',
  'seal-detail', 'edit-user', 'revision-record', 'flow-match',
];

export class TestRunner {
  constructor() {
    this.results = [];
    this.jsErrors = [];
    this.suiteStats = new Map();
  }

  attachPage(page) {
    page.on('pageerror', (e) => this.jsErrors.push(e.message));
    page.on('dialog', async (d) => {
      try {
        await d.accept();
      } catch {
        /* ignore */
      }
    });
  }

  assert(suite, name, ok, detail = '') {
    const step = `[${suite}] ${name}`;
    this.results.push({ suite, step, ok, detail: String(detail || '') });
    if (!this.suiteStats.has(suite)) this.suiteStats.set(suite, { pass: 0, fail: 0 });
    const s = this.suiteStats.get(suite);
    if (ok) s.pass += 1;
    else s.fail += 1;
    console.log(`${ok ? '✓' : '✗'} ${step}${detail ? ` — ${detail}` : ''}`);
    return ok;
  }

  summary() {
    const failed = this.results.filter((r) => !r.ok);
    const passed = this.results.length - failed.length;
    console.log(`\n========== 汇总：${passed}/${this.results.length} 通过 ==========`);
    console.log('\n分套件：');
    for (const [suite, st] of this.suiteStats) {
      console.log(`  ${suite}: ${st.pass}/${st.pass + st.fail}`);
    }
    if (failed.length) {
      console.log('\n失败项：');
      failed.forEach((f) => console.log(`  - ${f.step}: ${f.detail}`));
    }
    if (this.jsErrors.length) {
      console.log('\nJS 页面错误：');
      this.jsErrors.forEach((e) => console.log(`  - ${e}`));
    }
    return failed.length || this.jsErrors.length ? 1 : 0;
  }
}

export function sleep(ms = DELAY) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function launchBrowser() {
  const launchOpts = { headless: true, args: ['--no-sandbox'] };
  try {
    const ep = puppeteer.executablePath?.();
    if (ep) launchOpts.executablePath = ep;
  } catch {
    /* 使用 puppeteer 默认解析 */
  }
  const browser = await puppeteer.launch(launchOpts);
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  return { browser, page };
}

export async function evalPage(page, fn, ...args) {
  return page.evaluate(fn, ...args);
}

export async function setRole(page, role, strictRbac = false) {
  await evalPage(page, (r, strict) => {
    document.getElementById('role-select').value = r;
    if (state) state.strictRbac = strict;
    const toggle = document.getElementById('strict-rbac-toggle');
    if (toggle) toggle.checked = strict;
    switchRole(r);
  }, role, strictRbac);
  await sleep(150);
}

export async function activePageId(page) {
  return evalPage(page, () => document.querySelector('.page.active')?.id?.replace('page-', '') || null);
}

export async function isPageVisible(page, pageId) {
  return evalPage(page, (id) => {
    const el = document.getElementById(`page-${id}`);
    if (!el) return { ok: false, reason: 'missing' };
    return {
      ok: el.classList.contains('active') && el.offsetParent !== null,
      active: el.classList.contains('active'),
      visible: el.offsetParent !== null,
      nested: !!el.parentElement?.closest('.page:not(#page-' + id + ')'),
    };
  }, pageId);
}

export async function go(page, pageId) {
  await evalPage(page, (id) => {
    if (typeof switchPage === 'function') switchPage(id);
  }, pageId);
  await sleep(180);
  const v = await isPageVisible(page, pageId);
  return v.ok;
}

export async function clickSel(page, selector) {
  return page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) return { ok: false, reason: `未找到 ${sel}` };
    if (el.disabled) return { ok: true, skipped: 'disabled' };
    el.click();
    return { ok: true };
  }, selector);
}

export async function clickInActivePage(page, selector) {
  return page.evaluate((sel) => {
    const pageEl = document.querySelector('.page.active');
    if (!pageEl) return { ok: false, reason: '无活动页' };
    const el = pageEl.querySelector(sel);
    if (!el) return { ok: false, reason: `未找到 ${sel}` };
    if (el.disabled) return { ok: true, skipped: 'disabled' };
    el.click();
    return { ok: true };
  }, selector);
}

export async function hideAllModals(page) {
  await page.evaluate(() => {
    document.querySelectorAll('.modal-overlay.show').forEach((m) => m.classList.remove('show'));
    document.querySelectorAll('.edit-finding-modal.show').forEach((m) => m.classList.remove('show'));
    const report = document.getElementById('report-template-modal');
    if (report) report.classList.remove('show');
    const tour = document.getElementById('tour-hint');
    if (tour) tour.style.display = 'none';
  });
}

export async function toastText(page) {
  return evalPage(page, () => document.getElementById('toast-text')?.textContent || '');
}

export async function toastHas(page, pattern) {
  const t = await toastText(page);
  return pattern instanceof RegExp ? pattern.test(t) : (t && t.includes(pattern));
}

export async function modalOpen(page, id) {
  return evalPage(page, (id) => document.getElementById(`modal-${id}`)?.classList.contains('show'), id);
}

export async function prepareAdmin(page) {
  await page.goto(BASE, { waitUntil: 'networkidle0', timeout: 30000 });
  await page.waitForSelector('#page-dashboard.active');
  await setRole(page, 'admin', false);
}
