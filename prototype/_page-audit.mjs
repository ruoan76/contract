/**
 * 逐页结构与健康检查：motion.div 平衡、DOM 嵌套、切换可见性、标题映射
 * 运行：cd prototype && node _page-audit.mjs
 */
import { readFileSync, readdirSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import {
  TestRunner,
  launchBrowser,
  prepareAdmin,
  isPageVisible,
  ALL_PAGE_IDS,
  PAGE_TITLES,
  sleep,
} from './_test-lib.mjs';

const __dir = dirname(fileURLToPath(import.meta.url));
const PAGES_DIR = join(__dir, 'pages');

function divBalance(html) {
  let stack = 0;
  const re = /<\/?div(?:\s|>)/g;
  let m;
  while ((m = re.exec(html))) {
    stack += m[0].startsWith('</') ? -1 : 1;
  }
  return stack;
}

function auditSourceFiles() {
  const order = readFileSync(join(PAGES_DIR, '_order.txt'), 'utf8')
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean);
  const files = readdirSync(PAGES_DIR).filter((f) => f.startsWith('page-') && f.endsWith('.html'));
  const issues = [];

  for (const f of files) {
    const pid = f.replace('.html', '');
    if (!order.includes(pid)) {
      issues.push({ level: 'warn', page: pid, msg: '文件存在但未列入 _order.txt' });
    }
  }
  for (const pid of order) {
    const path = join(PAGES_DIR, `${pid}.html`);
    try {
      const html = readFileSync(path, 'utf8');
      const bal = divBalance(html);
      if (bal !== 0) {
        issues.push({ level: 'error', page: pid, msg: `div 标签不平衡 (差值 ${bal > 0 ? '+' : ''}${bal})` });
      }
      const expectedId = `page-${pid.replace('page-', '')}`;
      const idMatch = html.match(/id="(page-[^"]+)"/);
      if (idMatch && idMatch[1] !== expectedId) {
        issues.push({ level: 'error', page: pid, msg: `根 id 应为 ${expectedId}，实际为 ${idMatch[1]}` });
      }
    } catch {
      issues.push({ level: 'error', page: pid, msg: '缺少页面文件' });
    }
  }
  return { order, issues };
}

async function auditBuiltDom(page) {
  return page.evaluate((allIds) => {
    const content = document.querySelector('.content');
    const results = [];
    const dupIds = [];
    const seen = new Map();
    document.querySelectorAll('[id]').forEach((e) => {
      seen.set(e.id, (seen.get(e.id) || 0) + 1);
    });
    for (const [id, count] of seen) {
      if (count > 1) dupIds.push({ id, count });
    }
    for (const id of allIds) {
      const el = document.getElementById(`page-${id}`);
      if (!el) {
        results.push({ id, ok: false, reason: 'DOM 中不存在' });
        continue;
      }
      const parentPage = el.parentElement?.closest('.page');
      const nestedIn = parentPage && parentPage !== el ? parentPage.id : null;
      results.push({
        id,
        ok: content?.contains(el) && !nestedIn,
        nestedIn,
        directChild: el.parentElement === content,
      });
    }
    return { results, dupIds };
  }, ALL_PAGE_IDS);
}

async function auditPageTitles(page, r) {
  for (const id of ALL_PAGE_IDS) {
    await page.evaluate((pageId) => switchPage(pageId), id);
    await sleep(80);
    const title = await page.evaluate(() => document.getElementById('page-title')?.textContent || '');
    const expected = PAGE_TITLES[id];
    r.assert('结构', `标题 ${id}`, title === expected, title);
    const vis = await isPageVisible(page, id);
    r.assert('结构', `可见 ${id}`, vis.ok);
  }
}

/**
 * @param {{ quietSummary?: boolean }} opts
 * @returns {number} exit code
 */
export async function runAudit(opts = {}) {
  const r = new TestRunner();
  const { order, issues: srcIssues } = auditSourceFiles();

  console.log('\n=== 结构审计：源码 pages/*.html ===\n');
  console.log(`构建顺序：${order.length} 页`);
  if (srcIssues.length === 0) {
    r.assert('源码', 'div 平衡与 order', true);
  } else {
    for (const i of srcIssues) {
      r.assert('源码', i.page, i.level !== 'error', i.msg);
    }
  }

  const { browser, page } = await launchBrowser();
  r.attachPage(page);
  await prepareAdmin(page);

  console.log('\n=== 结构审计：index.html DOM ===\n');
  const { results, dupIds } = await auditBuiltDom(page);
  for (const row of results) {
    const detail = !row.ok
      ? row.reason || (row.nestedIn ? `嵌套于 ${row.nestedIn}` : '异常')
      : row.directChild
        ? 'content 直接子节点'
        : '在 content 内';
    r.assert('DOM', row.id, row.ok, detail);
  }
  r.assert('DOM', '无重复 id', dupIds.length === 0, dupIds.length ? `${dupIds.length} 个重复` : '0');

  console.log('\n=== 结构审计：标题与可见性 ===\n');
  await auditPageTitles(page, r);

  await browser.close();

  if (!opts.quietSummary) {
    console.log('\n--- 结构审计汇总 ---');
  }
  const code = r.summary();
  const srcErrors = srcIssues.filter((i) => i.level === 'error').length;
  return code || srcErrors ? 1 : 0;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const code = await runAudit();
  process.exit(code);
}
