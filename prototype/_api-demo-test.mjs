#!/usr/bin/env node
/**
 * 真实 API DEMO 联调测试（需 backend 已启动且 seed_dev 已执行）
 * 运行：cd prototype && node _api-demo-test.mjs
 */
const BASE = process.env.API_BASE_URL || 'http://127.0.0.1:8000';

async function login(username) {
  const url = `${BASE}/api/v1/system/login?username=${username}&password=123456`;
  const res = await fetch(url, { method: 'POST' });
  const json = await res.json();
  if (!res.ok || json.code !== 200) throw new Error(`登录失败 ${username}: ${JSON.stringify(json)}`);
  return json.data.token;
}

async function api(token, method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(json.detail || res.statusText);
    err.status = res.status;
    throw err;
  }
  return json.data !== undefined ? json.data : json;
}

async function runDemo01() {
  let t = await login('drafter1');
  const c = await api(t, 'POST', '/api/v1/contracts/', {
    title: 'Node DEMO-01',
    contract_type: 'purchase',
    counterparty_name: '供应商A',
    amount: 80000,
    content: '采购合同内容',
  });
  const flow = await api(t, 'POST', '/api/v1/approvals/submit', {
    contract_id: c.id,
    flow_type: 'simple',
  });
  t = await login('approver1');
  await api(t, 'POST', `/api/v1/approvals/${flow.flow_id}/approve`, {
    action: 'approve',
  });
  t = await login('drafter1');
  await api(t, 'POST', '/api/v1/ai-review/review', { contract_id: c.id });
  t = await login('legal1');
  await api(t, 'POST', `/api/v1/reviews/contracts/${c.id}/opinions`, {
    role: 'legal',
    action: 'approve',
  });
  t = await login('drafter1');
  const seal = await api(t, 'POST', '/api/v1/seals/apply', {
    contract_id: c.id,
    seal_type: '公章',
  });
  t = await login('admin');
  await api(t, 'POST', `/api/v1/seals/${seal.id}/approve`, { approved: true });
  t = await login('drafter1');
  const detail = await api(t, 'GET', `/api/v1/contracts/${c.id}`);
  if (detail.status !== 'sealed') throw new Error(`DEMO-01 期望 sealed 实际 ${detail.status}`);
  console.log('✓ DEMO-01 sealed', c.id);
}

async function runDemo04() {
  let t = await login('admin');
  const suffix = Date.now();
  const cp = await api(t, 'POST', '/api/v1/counterparties/', {
    name: 'Node黑名单公司' + suffix,
    credit_code: '91110000' + String(suffix).slice(-8),
  });
  await api(t, 'POST', `/api/v1/counterparties/${cp.id}/blacklist`, { reason: 'test' });
  t = await login('drafter1');
  try {
    await api(t, 'POST', '/api/v1/contracts/', {
      title: '应拒绝',
      contract_type: 'purchase',
      counterparty_id: cp.id,
      counterparty_name: cp.name,
      amount: 50000,
      content: 'x',
    });
    throw new Error('DEMO-04 应 403');
  } catch (e) {
    if (e.status !== 403) throw e;
  }
  console.log('✓ DEMO-04 blacklist 403');
}

async function runDemo05() {
  let t = await login('drafter1');
  const c = await api(t, 'POST', '/api/v1/contracts/', {
    title: 'Node DEMO-05',
    contract_type: 'service',
    counterparty_name: '客户C',
    amount: 150000,
    content: '原始内容',
  });
  const flow = await api(t, 'POST', '/api/v1/approvals/submit', {
    contract_id: c.id,
    flow_type: 'standard',
  });
  t = await login('approver1');
  await api(t, 'POST', `/api/v1/approvals/${flow.flow_id}/approve`, { action: 'approve' });
  t = await login('legal1');
  await api(t, 'POST', `/api/v1/reviews/contracts/${c.id}/return`, {
    role: 'legal',
    comment: '请修改',
  });
  t = await login('drafter1');
  const rev = await api(t, 'POST', `/api/v1/contracts/${c.id}/revisions`, {
    content: '修订后',
    change_description: '修改条款',
  });
  await api(t, 'POST', '/api/v1/ai-review/review', { contract_id: c.id });
  if (rev.version !== 2) throw new Error('DEMO-05 version 期望 2');
  console.log('✓ DEMO-05 revision v2', c.id);
}

async function runDemo03() {
  let t = await login('drafter1');
  const c = await api(t, 'POST', '/api/v1/contracts/', {
    title: 'Node DEMO-03',
    contract_type: 'purchase',
    counterparty_name: '大客户',
    amount: 2500000,
    content: '大额',
  });
  const flow = await api(t, 'POST', '/api/v1/approvals/submit', {
    contract_id: c.id,
    flow_type: 'large_amount',
  });
  const hist = await api(t, 'GET', `/api/v1/approvals/${flow.flow_id}/history`);
  if ((hist.total_steps || 0) < 5) throw new Error('DEMO-03 steps');
  console.log('✓ DEMO-03 history steps', hist.total_steps);
}

async function runDemo02() {
  let t = await login('drafter1');
  const c = await api(t, 'POST', '/api/v1/contracts/', {
    title: 'Node DEMO-02',
    contract_type: 'service',
    counterparty_name: '客户B',
    amount: 320000,
    content: '服务合同内容',
  });
  await api(t, 'POST', '/api/v1/ai-review/review', { contract_id: c.id });
  const flow = await api(t, 'POST', '/api/v1/approvals/submit', {
    contract_id: c.id,
    flow_type: 'standard',
  });
  for (const user of ['approver1', 'legal1', 'finance1', 'executive1']) {
    t = await login(user);
    const pending = await api(t, 'GET', '/api/v1/approvals/pending');
    const item = (pending.items || []).find((i) => i.contract_id === c.id);
    if (item) {
      await api(t, 'POST', `/api/v1/approvals/${item.flow_id}/approve`, { action: 'approve' });
    }
  }
  t = await login('legal1');
  await api(t, 'POST', `/api/v1/reviews/contracts/${c.id}/opinions`, { role: 'legal', action: 'approve' });
  t = await login('finance1');
  await api(t, 'POST', `/api/v1/reviews/contracts/${c.id}/opinions`, { role: 'finance', action: 'approve' });
  t = await login('executive1');
  await api(t, 'POST', `/api/v1/reviews/contracts/${c.id}/opinions`, { role: 'executive', action: 'approve' });
  t = await login('admin');
  await api(t, 'POST', `/api/v1/archives/${c.id}/archive`, { archive_location: '/archive/demo02' });
  t = await login('drafter1');
  const detail = await api(t, 'GET', `/api/v1/contracts/${c.id}`);
  if (detail.status !== 'archived') throw new Error('DEMO-02 archived');
  console.log('✓ DEMO-02 archived', c.id);
}

async function main() {
  const health = await fetch(`${BASE}/health`);
  if (!health.ok) {
    console.error('后端未启动:', BASE);
    process.exit(1);
  }
  console.log('API 联调测试', BASE);
  await runDemo01();
  await runDemo04();
  await runDemo05();
  await runDemo02();
  await runDemo03();
  console.log('全部通过 (DEMO-01~05)');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
