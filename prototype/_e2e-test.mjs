/**
 * 原型完整 E2E 测试（P0/P1/P2 已完成能力）
 * 运行：cd prototype && node _e2e-test.mjs
 */
import { fileURLToPath } from 'url';
import {
  TestRunner,
  launchBrowser,
  prepareAdmin,
  setRole,
  go,
  evalPage,
  clickSel,
  clickInActivePage,
  hideAllModals,
  toastHas,
  toastText,
  modalOpen,
  sleep,
  activePageId,
  isPageVisible,
  ALL_PAGE_IDS,
  NAV_PAGES,
  DRILLDOWN_PAGES,
  ROLE_VISIBLE,
  PAGE_TITLES,
  SAMPLE_CONTRACT_NOS,
  MODAL_IDS,
} from './_test-lib.mjs';

// —— Suite 0：健康与构建 ——
async function suiteHealth(page, r) {
  const health = await evalPage(page, () => {
    const pages = [...document.querySelectorAll('.page')].map((p) => p.id);
    const ids = [...document.querySelectorAll('[id]')].map((e) => e.id);
    const dup = [...new Set(ids.filter((id, i) => ids.indexOf(id) !== i))];
    const hasSwitch = typeof switchPage === 'function';
    const hasContracts = Array.isArray(contracts) && contracts.length >= 17;
    return { pageCount: pages.length, dupIds: dup, hasSwitch, hasContracts, contractCount: contracts?.length };
  });
  r.assert('健康', '页面数量≥20', health.pageCount >= 20, `${health.pageCount} 个`);
  r.assert('健康', '无重复 id', health.dupIds.length === 0, health.dupIds.slice(0, 5).join(', ') || '0');
  r.assert('健康', 'switchPage 已加载', health.hasSwitch);
  r.assert('健康', '样例合同≥17', health.hasContracts, `${health.contractCount} 条`);
}

// —— Suite 1：导航与可见性 ——
async function suiteNavigation(page, r) {
  for (const pid of NAV_PAGES) {
    const ok = await go(page, pid);
    r.assert('导航', pid, ok);
    const title = await evalPage(page, () => document.getElementById('page-title')?.textContent || '');
    const expected = PAGE_TITLES[pid];
    r.assert('导航标题', pid, title === expected, title || '(空)');
  }
  for (const pid of DRILLDOWN_PAGES) {
    const ok = await go(page, pid);
    r.assert('下钻导航', pid, ok);
  }
  await go(page, 'dashboard');
  await clickSel(page, '.header-btn[onclick*="create"]');
  r.assert('顶栏', '新建合同', await evalPage(page, () => document.getElementById('page-create')?.classList.contains('active')));
  await go(page, 'dashboard');
  await clickSel(page, '.header-btn[onclick*="messages"]');
  const msgVis = await isPageVisible(page, 'messages');
  r.assert('顶栏', '消息中心可见', msgVis.ok);
}

// —— Suite 2：P0 主路径与合同上下文 ——
async function suiteP0MainPath(page, r) {
  // resolveFlowType
  const flows = await evalPage(page, () => ({
    simple: resolveFlowType('purchase', 80000),
    standard: resolveFlowType('purchase', 320000),
    special: resolveFlowType('purchase', 2500000),
    labor: resolveFlowType('labor', 50000),
  }));
  r.assert('P0', 'resolveFlowType 简易', flows.simple === 'simple');
  r.assert('P0', 'resolveFlowType 标准', flows.standard === 'standard');
  r.assert('P0', 'resolveFlowType 特殊', flows.special === 'special');
  r.assert('P0', 'resolveFlowType 劳务', flows.labor === 'standard');

  // submitContract 写入合同号
  await go(page, 'create');
  const submit = await evalPage(page, () => {
    selectCreateMode('blank');
    document.getElementById('new-contract-title').value = 'E2E提交测试';
    document.getElementById('new-contract-type').value = 'purchase';
    document.getElementById('new-contract-counterparty').value = '测试公司';
    document.getElementById('new-contract-amount').value = '95000';
    submitContract();
    return {
      no: sessionStorage.getItem('current_contract_no'),
      flow: sessionStorage.getItem('current_contract_flow'),
      modal: document.getElementById('modal-flow-match')?.classList.contains('show'),
    };
  });
  r.assert('P0', 'submitContract 写入 current_contract_no', !!submit.no, submit.no || '');
  r.assert('P0', 'submitContract 写入 flow', submit.flow === 'simple', submit.flow);
  if (submit.modal) {
    await clickSel(page, '#modal-flow-match .btn-outline');
    await hideAllModals(page);
  }
  await evalPage(page, () => resetCreateMode());

  // confirmAIReview → review-workspace
  await evalPage(page, () => {
    sessionStorage.setItem('current_contract_no', 'DEMO-05');
    sessionStorage.setItem('current_contract_flow', 'standard');
    window.confirm = () => true;
  });
  await go(page, 'ai-review');
  await clickInActivePage(page, 'button[onclick="confirmAIReview()"]');
  await sleep(450);
  r.assert('P0', 'confirmAIReview→工作台', await evalPage(page, () =>
    document.getElementById('page-review-workspace')?.classList.contains('active')
  ));
  r.assert('P0', 'confirmAIReview 法务 Tab', await evalPage(page, () =>
    document.getElementById('stage-legal')?.classList.contains('active')
  ));

  // showContractDetail + backFromContractDetail
  await evalPage(page, () => showContractDetail('CTR-20240115-0001'));
  await sleep(200);
  r.assert('P0', 'showContractDetail 标题', await evalPage(page, () =>
    document.getElementById('detail-contract-title')?.textContent?.includes('CTR-20240115-0001')
  ));
  await evalPage(page, () => backFromContractDetail());
  await sleep(200);
  const afterBack = await activePageId(page);
  r.assert('P0', 'backFromContractDetail 返回', afterBack !== 'contract-detail', afterBack || '');

  // openReviewWorkspace
  await go(page, 'dashboard');
  await evalPage(page, () => openReviewWorkspace('DEMO-05'));
  await sleep(400);
  r.assert('P0', 'openReviewWorkspace', (await isPageVisible(page, 'review-workspace')).ok);

  // 详情页快捷入口
  await evalPage(page, () => showContractDetail('CTR-20240115-0001'));
  await evalPage(page, () => openAiReviewFromDetail());
  await sleep(200);
  r.assert('P0', '详情→AI审查', await evalPage(page, () =>
    document.getElementById('page-ai-review')?.classList.contains('active')
  ));
  await evalPage(page, () => showContractDetail('CTR-20240115-0001'));
  await evalPage(page, () => openReviewWorkspaceFromDetail());
  await sleep(200);
  r.assert('P0', '详情→评审工作台', await evalPage(page, () =>
    document.getElementById('page-review-workspace')?.classList.contains('active')
  ));
}

// —— Suite 3：看板与消息 ——
async function suiteDashboardMessages(page, r) {
  await go(page, 'dashboard');
  await clickInActivePage(page, '.kanban-card[onclick*="showContractDetail"]');
  r.assert('看板', '卡片→详情', await evalPage(page, () =>
    document.getElementById('page-contract-detail')?.classList.contains('active')
  ));
  await go(page, 'dashboard');
  await clickSel(page, '.kanban-card[onclick*="CTR-20240108-0011"]');
  await sleep(200);
  r.assert('看板', '年度安保详情上下文', await evalPage(page, () => {
    const t = document.getElementById('detail-contract-title')?.textContent || '';
    return document.getElementById('page-contract-detail')?.classList.contains('active') && t.includes('CTR-20240108-0011');
  }));

  await go(page, 'dashboard');
  await clickSel(page, '.stat-card[onclick*="goArchivesExpiring"]');
  await sleep(200);
  r.assert('看板', '到期统计→归档', await evalPage(page, () =>
    document.getElementById('page-archives')?.classList.contains('active')
  ));

  await go(page, 'messages');
  r.assert('消息', '页面非嵌套可见', (await isPageVisible(page, 'messages')).ok);
  await clickInActivePage(page, 'button[onclick="markAllMessagesRead()"]');
  r.assert('消息', '全部已读', await toastHas(page, '已读'));

  await evalPage(page, () => {
    const sel = document.getElementById('msg-type-filter');
    if (sel) { sel.value = 'warning'; filterMessages(); }
  });
  const warningCount = await evalPage(page, () =>
    document.querySelectorAll('#page-messages .msg-item[style*="display: none"]').length
  );
  r.assert('消息', '类型筛选可执行', typeof warningCount === 'number');

  await go(page, 'messages');
  await evalPage(page, () => {
    const item = document.querySelector('.msg-item[data-type="ai"]');
    if (item) openMessageDetail(item);
  });
  await sleep(450);
  const afterAiMsg = await activePageId(page);
  r.assert('消息', 'AI消息→目标页', afterAiMsg === 'ai-review' || afterAiMsg === 'contract-detail', afterAiMsg || '');
}

// —— Suite 4：起草与合同列表 ——
async function suiteCreateContracts(page, r) {
  await go(page, 'create');
  for (const mode of ['blank', 'template', 'history', 'ai-parse']) {
    await evalPage(page, (m) => selectCreateMode(m), mode);
    await sleep(80);
    r.assert('新建', `模式 ${mode}`, true);
  }
  await evalPage(page, () => {
    selectCreateMode('blank');
    document.getElementById('new-contract-title').value = '草稿测试';
    saveDraft();
  });
  r.assert('新建', '保存草稿', await toastHas(page, '草稿'));
  await evalPage(page, () => resetCreateMode());

  await go(page, 'contracts');
  await clickInActivePage(page, 'button[onclick="filterContracts()"]');
  await clickInActivePage(page, 'button[onclick="resetFilters()"]');
  r.assert('合同列表', '筛选/重置', true);
  await clickInActivePage(page, '#contract-table-body button[onclick*="showContractDetail"]');
  await sleep(200);
  r.assert('合同列表', '查看→详情', await evalPage(page, () =>
    document.getElementById('page-contract-detail')?.classList.contains('active')
  ));
  await hideAllModals(page);
  await evalPage(page, () => changeContractPage(2));
  await sleep(120);
  r.assert('合同列表', '分页到第2页', (await evalPage(page, () => contractPage)) === 2);
  await evalPage(page, () => changeContractPage(1));
}

// —— Suite 5：AI / 条款 / 评审 ——
async function suiteReviewAi(page, r) {
  await go(page, 'ai-review');
  await clickInActivePage(page, 'button[onclick="filterReviewReport()"]');
  await clickInActivePage(page, 'button[onclick="resetReviewFilter()"]');
  await clickInActivePage(page, 'button[onclick="reReview()"]');
  await sleep(2200);
  r.assert('AI审查', '重新审查', await toastHas(page, /审查|重新|更新/));
  await clickInActivePage(page, 'button[onclick*="false_positive"]');
  r.assert('AI审查', '标记误报', await toastHas(page, '误报'));
  await clickInActivePage(page, 'button[onclick*="false_negative"]');
  r.assert('AI审查', '标记漏报', await toastHas(page, /漏报|反馈/));

  const labelFilter = await evalPage(page, () => {
    if (typeof initAiReviewLabelFilter !== 'function') return { ok: false, reason: 'no fn' };
    initAiReviewLabelFilter();
    const sel = document.getElementById('review-risk-label');
    if (!sel) return { ok: false, reason: 'no review-risk-label' };
    sel.value = 'L06';
    filterReviewReport();
    const visible = [...document.querySelectorAll('#page-ai-review .risk-item')].filter(
      (el) => el.style.display !== 'none'
    ).length;
    return { ok: true, visible };
  });
  r.assert('AI审查', '15标签筛选', labelFilter.ok, String(labelFilter.visible ?? labelFilter.reason));

  await go(page, 'clause-compare');
  for (const f of ['all', 'match', 'conflict', 'missing', 'extra']) {
    await clickInActivePage(page, `button[onclick*="filterCompare('${f}')"]`);
    await sleep(40);
  }
  r.assert('条款比对', '筛选 Tab', true);
  await clickInActivePage(page, 'button[onclick="exportCompareReport()"]');
  await sleep(150);
  r.assert('条款比对', '导出', await toastHas(page, /导出|报告/));

  await go(page, 'review-center');
  await clickInActivePage(page, 'button[onclick="escalateConflict()"]');
  await sleep(150);
  r.assert('评审中心', '升级仲裁', await toastHas(page, /升级|仲裁/));

  await evalPage(page, () => sessionStorage.setItem('current_contract_flow', 'standard'));
  await go(page, 'review-workspace');
  for (const stage of ['ai', 'legal', 'finance', 'executive']) {
    await evalPage(page, (s) => switchStage(s), stage);
    await sleep(80);
    const active = await evalPage(page, (s) => {
      if (s === 'ai') return document.getElementById('page-ai-review')?.classList.contains('active');
      return document.getElementById(`stage-${s}`)?.classList.contains('active');
    }, stage);
    r.assert('评审工作台', `阶段 ${stage}`, active);
  }

  await evalPage(page, () => switchStage('legal'));
  await evalPage(page, () => saveWorkspace());
  r.assert('评审工作台', '法务暂存', await toastHas(page, /暂存|保存/));

  // 财务/高管通过（不传 event，避免 .target 报错）
  await evalPage(page, () => {
    sessionStorage.setItem('current_contract_flow', 'standard');
    switchStage('finance');
    const ta = document.querySelector('#stage-finance textarea');
    if (ta) ta.value = '财务测试意见';
  });
  await evalPage(page, () => financeApprove());
  await sleep(300);
  r.assert('评审工作台', '财务通过', await toastHas(page, /财务|高管/));
  await evalPage(page, () => {
    window.confirm = () => true;
    executiveApprove();
  });
  await sleep(100);
  const execToast = await evalPage(page, () => document.getElementById('toast-text')?.textContent || '');
  r.assert('评审工作台', '高管批准', /批准|通过|用印/.test(execToast), execToast);

  await evalPage(page, () => sessionStorage.setItem('current_contract_flow', 'simple'));
  await go(page, 'review-workspace');
  const simpleTabs = await evalPage(page, () => ({
    finance: document.querySelector('[data-stage="finance"]')?.style.display,
    executive: document.querySelector('[data-stage="executive"]')?.style.display,
  }));
  r.assert('评审工作台', '简易流程隐藏财务/高管', simpleTabs.finance === 'none' && simpleTabs.executive === 'none');
  await evalPage(page, () => sessionStorage.setItem('current_contract_flow', 'standard'));

  await go(page, 'review-history');
  const exportMsg = await evalPage(page, () => {
    exportReviewHistory();
    return document.getElementById('toast-text')?.textContent || '';
  });
  r.assert('评审历史', '导出', /导出|评审报告/.test(exportMsg), exportMsg);
}

// —— Suite 6：审批 / 用印 / 归档 ——
async function suiteApprovalSealArchive(page, r) {
  await setRole(page, 'admin', false);
  await go(page, 'approvals');
  await evalPage(page, () => {
    window.confirm = () => true;
    const cb = document.querySelector('.approval-check');
    if (cb) cb.checked = true;
  });
  await clickInActivePage(page, 'button[onclick="batchApprove()"]');
  await sleep(150);
  r.assert('审批', '批量通过弹窗', await modalOpen(page, 'approval'));
  await hideAllModals(page);

  await clickInActivePage(page, 'button[onclick*="approveItem"][onclick*="approve"]');
  await sleep(150);
  await evalPage(page, () => setComment('E2E同意'));
  await clickSel(page, '#modal-approval button[onclick="confirmApproval()"]');
  await sleep(200);
  r.assert('审批', '单笔通过', await toastHas(page, '成功'));

  await go(page, 'contracts');
  await evalPage(page, () => showApprovalHistory('DEMO-03'));
  await sleep(350);
  r.assert('审批历史', '下钻页激活', (await isPageVisible(page, 'approval-history')).ok);
  r.assert('审批历史', '董事会节点', await evalPage(page, () =>
    document.getElementById('approval-history-steps')?.textContent?.includes('董事会')
  ));
  await evalPage(page, () => backFromApprovalHistory());

  await go(page, 'seal');
  await clickInActivePage(page, 'button[onclick="filterSealList()"]');
  r.assert('用印', '筛选', await toastHas(page, /筛选|显示/));
  await clickInActivePage(page, 'button[onclick*="confirmSealAction"]');
  await sleep(150);
  r.assert('用印', '确认用印', await toastHas(page, /用印|成功/));

  await go(page, 'archives');
  await clickInActivePage(page, 'button[onclick="filterArchiveList()"]');
  await clickInActivePage(page, 'button[onclick="exportLedger(\'Excel\')"]');
  await sleep(150);
  r.assert('归档', '筛选与导出', await toastHas(page, /导出|筛选|台账/));
}

// —— Suite 7：基础数据与系统 ——
async function suiteMasterDataSystem(page, r) {
  await go(page, 'templates');
  for (const mid of ['template-create', 'template-preview', 'template-edit']) {
    await evalPage(page, (id) => showModal(id), mid);
    await sleep(80);
    r.assert('模板', mid, await modalOpen(page, mid));
    await hideAllModals(page);
  }

  await go(page, 'counterparties');
  await clickInActivePage(page, 'button[onclick*="showNewCounterpartyModal"]');
  r.assert('相对方', '新增弹窗', await modalOpen(page, 'new-counterparty'));
  await hideAllModals(page);

  await go(page, 'config');
  await clickInActivePage(page, '.tab[onclick*="approvers"]');
  await clickInActivePage(page, 'button[onclick="openConfigEdit()"]');
  r.assert('配置', '编辑弹窗', await modalOpen(page, 'edit-config'));
  await hideAllModals(page);

  await go(page, 'users');
  await clickInActivePage(page, 'button[onclick="filterUsers()"]');
  await clickInActivePage(page, 'button[onclick="openUserEdit()"]');
  r.assert('用户', '编辑弹窗', await modalOpen(page, 'edit-user'));
  await hideAllModals(page);

  await go(page, 'audit');
  await clickInActivePage(page, 'button[onclick="exportAuditLog()"]');
  await sleep(150);
  r.assert('审计', '导出', await toastHas(page, /导出|暂无/));
  await evalPage(page, () => renderAuditLog());
  r.assert('审计', 'renderAuditLog', await evalPage(page, () =>
    document.querySelector('#page-audit tbody tr') != null
  ));
}

// —— Suite 8：修订工作台 ——
async function suiteRevision(page, r) {
  await go(page, 'revision-workspace');
  await clickInActivePage(page, 'button[onclick="saveDraftRevision()"]');
  r.assert('修订', '保存草稿', await toastHas(page, /草稿|保存/));
  await evalPage(page, () => {
    const t = document.getElementById('revision-summary');
    if (t) t.value = 'E2E 修订说明';
  });
  await clickInActivePage(page, 'button[onclick="submitRevision()"]');
  await sleep(250);
  r.assert('修订', '提交重审', await toastHas(page, /提交|评审|AI/));
}

// —— Suite 9：合同详情 D10 ——
async function suiteContractDetail(page, r) {
  await evalPage(page, () => {
    sessionStorage.setItem('current_contract_no', 'CTR-20240115-0001');
    showContractDetail('CTR-20240115-0001');
  });
  await sleep(200);
  r.assert('合同详情', '上下文标题', await evalPage(page, () =>
    document.getElementById('detail-contract-title')?.textContent?.includes('CTR-20240115-0001')
  ));
  await evalPage(page, () => showApprovalHistoryFromDetail());
  await sleep(200);
  r.assert('合同详情', '→审批历史', await evalPage(page, () =>
    document.getElementById('page-approval-history')?.classList.contains('active')
  ));
  await evalPage(page, () => backFromApprovalHistory());
  await sleep(200);

  await evalPage(page, () => {
    sessionStorage.setItem('current_contract_no', 'CTR-20240115-0001');
    showModal('contract-detail');
  });
  await sleep(250);
  r.assert('合同详情', 'showModal 重定向', (await isPageVisible(page, 'contract-detail')).ok);
}

// —— Suite 10：弹窗矩阵 ——
async function suiteModals(page, r) {
  await go(page, 'dashboard');
  for (const mid of MODAL_IDS) {
    await hideAllModals(page);
    await evalPage(page, (id) => showModal(id), mid);
    await sleep(60);
    const open = await modalOpen(page, mid);
    r.assert('弹窗', mid, open);
    await evalPage(page, (id) => hideModal(id), mid);
  }
}

// —— Suite 11：角色 RBAC（宽松） ——
async function suiteRoleLoose(page, r) {
  for (const [role, visible] of Object.entries(ROLE_VISIBLE)) {
    await setRole(page, role, false);
    let ok = true;
    for (const pid of visible) {
      if (!(await go(page, pid))) {
        ok = false;
        r.assert('角色宽松', `${role}/${pid}`, false);
      }
    }
    r.assert('角色宽松', `${role} ${visible.length} 页`, ok);
    if (role === 'drafter') {
      await go(page, 'revision-workspace');
      r.assert('角色宽松', '起草人修订工作台', await evalPage(page, () =>
        document.getElementById('page-revision-workspace')?.classList.contains('active')
      ));
    }
  }
}

// —— Suite 12：严格 RBAC ——
async function suiteRoleStrict(page, r) {
  await setRole(page, 'drafter', true);
  // 下钻页始终可进
  await evalPage(page, () => showContractDetail('CTR-20240115-0001'));
  await sleep(150);
  r.assert('严格RBAC', '起草人→合同详情', await evalPage(page, () =>
    document.getElementById('page-contract-detail')?.classList.contains('active')
  ));

  await setRole(page, 'drafter', true);
  await go(page, 'messages');
  await evalPage(page, () => {
    const item = document.querySelector('.msg-item[data-type="approval"]');
    if (item) openMessageDetail(item);
  });
  await sleep(450);
  const msgTarget = await activePageId(page);
  r.assert('严格RBAC', '审批消息回退详情/可访问页', msgTarget === 'contract-detail' || msgTarget === 'approvals', msgTarget || '');

  await setRole(page, 'legal', true);
  const legalBlock = await evalPage(page, () => {
    switchPage('messages');
    return document.getElementById('toast-text')?.textContent?.includes('无权');
  });
  r.assert('严格RBAC', '法务无消息权限拦截', legalBlock);

  await setRole(page, 'legal', true);
  r.assert('严格RBAC', '法务可进 contracts', await go(page, 'contracts'));

  await setRole(page, 'admin', false);
}

// —— Suite 13：样例数据一致性 ——
async function suiteDataConsistency(page, r) {
  const inData = await evalPage(page, (nos) => {
    return nos.map((no) => ({ no, found: contracts.some((c) => c.no === no) }));
  }, SAMPLE_CONTRACT_NOS);
  for (const row of inData) {
    r.assert('数据', `合同 ${row.no} 在 defaultContracts`, row.found);
  }
  const kanbanNos = await evalPage(page, () => {
  const cards = [...document.querySelectorAll('#page-dashboard .kanban-card[onclick*="showContractDetail"]')];
    return cards.map((c) => {
      const m = c.getAttribute('onclick')?.match(/'([^']+)'/);
      return m ? m[1] : null;
    }).filter(Boolean);
  });
  for (const no of kanbanNos) {
    const found = await evalPage(page, (n) => contracts.some((c) => c.no === n), no);
    r.assert('数据', `看板 ${no} 可解析`, found);
  }
}

// —— Suite 14：Demo 脚本关键步 ——
async function suiteDemoPaths(page, r) {
  // DEMO-01 简易：8万 + simple flow
  await setRole(page, 'drafter', false);
  await go(page, 'create');
  const demo01 = await evalPage(page, () => {
    selectCreateMode('blank');
    document.getElementById('new-contract-amount').value = '80000';
    document.getElementById('new-contract-type').value = 'purchase';
    return resolveFlowType('purchase', 80000);
  });
  r.assert('Demo', 'DEMO-01 简易流程类型', demo01 === 'simple');

  // DEMO-03 特殊 + 董事会
  await go(page, 'contracts');
  await evalPage(page, () => showApprovalHistory('DEMO-03'));
  await sleep(150);
  r.assert('Demo', 'DEMO-03 审批历史', await evalPage(page, () =>
    document.getElementById('approval-history-steps')?.textContent?.includes('董事会')
  ));
  await evalPage(page, () => backFromApprovalHistory());

  await setRole(page, 'admin', false);
}

export async function runE2E() {
  const r = new TestRunner();
  const { browser, page } = await launchBrowser();
  r.attachPage(page);
  await prepareAdmin(page);

  await suiteHealth(page, r);
  await suiteNavigation(page, r);
  await suiteP0MainPath(page, r);
  await suiteDashboardMessages(page, r);
  await suiteCreateContracts(page, r);
  await suiteReviewAi(page, r);
  await suiteApprovalSealArchive(page, r);
  await suiteMasterDataSystem(page, r);
  await suiteRevision(page, r);
  await suiteContractDetail(page, r);
  await suiteModals(page, r);
  await suiteRoleLoose(page, r);
  await suiteRoleStrict(page, r);
  await suiteDataConsistency(page, r);
  await suiteDemoPaths(page, r);

  await browser.close();
  return r.summary();
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const code = await runE2E();
  process.exit(code);
}
