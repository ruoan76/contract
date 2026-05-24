/**
 * DEMO 脚本 API 编排 — 对应 docs/design/demo-script-v1.md
 */
const ApiDemo = (function () {
  async function assertStatus(contractId, expectedStatus, label) {
    await ApiAuth.loginAsRole('drafter');
    const c = await ApiContracts.get(contractId);
    if (c.status !== expectedStatus) {
      throw new Error((label || '状态') + ' 期望 ' + expectedStatus + ' 实际 ' + c.status);
    }
    return c;
  }

  /** DEMO-01 简易全链路 */
  async function runDemo01() {
    ApiAuth.clearCache();
    await ApiAuth.loginAsRole('drafter');
    const created = await ApiContracts.create({
      title: 'DEMO-01 简易流程',
      contract_type: 'purchase',
      counterparty_name: '供应商A',
      amount: 80000,
      content: '采购合同内容，用于 AI 与评审测试。',
    });
    const cid = created.id;
    const flow = await ApiApprovals.submit(cid, 'simple');
    await ApiAuth.loginAsRole('approver');
    await ApiApprovals.approve(flow.flow_id, 'approve', '通过');
    await ApiAi.review(cid);
    await ApiAuth.loginAsRole('legal');
    await ApiReviews.submitOpinion(cid, 'legal', 'approve', '法务通过');
    await ApiAuth.loginAsRole('drafter');
    const seal = await ApiSeals.apply(cid, '公章');
    await ApiAuth.loginAsRole('admin');
    await ApiSeals.approve(seal.id, true);
    const finalC = await assertStatus(cid, 'sealed', 'DEMO-01');
    return { contractId: cid, status: finalC.status, demo: 'DEMO-01' };
  }

  /** DEMO-04 黑名单 */
  async function runDemo04() {
    ApiAuth.clearCache();
    await ApiAuth.loginAsRole('admin');
    const cp = await ApiCounterparties.create({
      name: '黑名单测试公司',
      credit_code: '91110000DEMO4001',
    });
    await ApiCounterparties.blacklist(cp.id, '联调测试');
    await ApiAuth.loginAsRole('drafter');
    try {
      await ApiContracts.create({
        title: '应被拒绝',
        contract_type: 'purchase',
        counterparty_id: cp.id,
        counterparty_name: cp.name,
        amount: 50000,
        content: 'x',
      });
      throw new Error('DEMO-04 期望 403 但创建成功');
    } catch (e) {
      if (e.status !== 403 && !String(e.message).includes('403')) throw e;
    }
    return { demo: 'DEMO-04', blocked: true };
  }

  /** DEMO-05 退回修订 */
  async function runDemo05() {
    ApiAuth.clearCache();
    await ApiAuth.loginAsRole('drafter');
    const created = await ApiContracts.create({
      title: 'DEMO-05 退回修订',
      contract_type: 'service',
      counterparty_name: '客户C',
      amount: 150000,
      content: '原始内容',
    });
    const cid = created.id;
    const flow = await ApiApprovals.submit(cid, 'standard');
    await ApiAuth.loginAsRole('approver');
    await ApiApprovals.approve(flow.flow_id, 'approve');
    await ApiAuth.loginAsRole('legal');
    await ApiReviews.returnForRevision(cid, 'legal', '请修改付款条款');
    await assertStatus(cid, 'draft', 'DEMO-05 退回');
    await ApiAuth.loginAsRole('drafter');
    const rev = await ApiContracts.submitRevision(cid, {
      content: '修订后内容',
      change_description: '修改付款条款',
    });
    await ApiAi.review(cid);
    return { contractId: cid, version: rev.version, demo: 'DEMO-05' };
  }

  /** DEMO-02 标准评审 + 归档 */
  async function runDemo02() {
    ApiAuth.clearCache();
    await ApiAuth.loginAsRole('drafter');
    const created = await ApiContracts.create({
      title: 'DEMO-02 标准评审',
      contract_type: 'service',
      counterparty_name: '客户B',
      amount: 320000,
      content: '服务合同条款内容，用于标准评审流程。',
    });
    const cid = created.id;
    await ApiAi.review(cid);
    const flow = await ApiApprovals.submit(cid, 'standard');
    await ApiApprovals.approveAllStepsForContract(cid);
    await ApiAuth.loginAsRole('legal');
    await ApiReviews.submitOpinion(cid, 'legal', 'approve');
    await ApiAuth.loginAsRole('finance');
    await ApiReviews.submitOpinion(cid, 'finance', 'approve');
    await ApiAuth.loginAsRole('executive');
    await ApiReviews.submitOpinion(cid, 'executive', 'approve');
    await ApiAuth.loginAsRole('admin');
    await ApiArchives.archive(cid, '/archive/2026/demo02');
    const finalC = await assertStatus(cid, 'archived', 'DEMO-02');
    return { contractId: cid, status: finalC.status, demo: 'DEMO-02' };
  }

  /** DEMO-03 特殊流程 history */
  async function runDemo03() {
    ApiAuth.clearCache();
    await ApiAuth.loginAsRole('drafter');
    const created = await ApiContracts.create({
      title: 'DEMO-03 特殊流程',
      contract_type: 'purchase',
      counterparty_name: '大客户',
      amount: 2500000,
      content: '大额合同内容',
    });
    const cid = created.id;
    const flow = await ApiApprovals.submit(cid, 'large_amount');
    const history = await ApiApprovals.history(flow.flow_id);
    if ((history.total_steps || 0) < 5) {
      throw new Error('DEMO-03 total_steps 期望 >=5 实际 ' + history.total_steps);
    }
    return { contractId: cid, total_steps: history.total_steps, demo: 'DEMO-03' };
  }

  async function runAll() {
    const results = [];
    results.push(await runDemo01());
    results.push(await runDemo04());
    results.push(await runDemo05());
    results.push(await runDemo02());
    results.push(await runDemo03());
    return results;
  }

  return {
    runDemo01: runDemo01,
    runDemo02: runDemo02,
    runDemo03: runDemo03,
    runDemo04: runDemo04,
    runDemo05: runDemo05,
    runAll: runAll,
  };
})();

if (typeof window !== 'undefined') {
  window.runDemo01 = ApiDemo.runDemo01;
  window.runDemo02 = ApiDemo.runDemo02;
  window.runDemo03 = ApiDemo.runDemo03;
  window.runDemo04 = ApiDemo.runDemo04;
  window.runDemo05 = ApiDemo.runDemo05;
  window.runAllDemos = ApiDemo.runAll;
}
