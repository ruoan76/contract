# 原型 P0/P1 改动清单（可执行）

> **版本**：1.0 | **日期**：2026-05-19  
> **依据**：[原型走查结论](../design/DESIGN_STATUS.md)（业务完整性 / 主路径断裂）  
> **实现范围**：`prototype/pages/*.html`、`prototype/partials/modals.html`、`prototype/js/02-app.js`（`build.py` 后同步 `index.html`）  
> **验收**：`cd prototype && python3 build.py && node _run-tests.mjs`（结构审计 + E2E 150+ 项）+ 手工走查两条 Demo 路径（见文末）

---

## 使用说明

| 字段 | 含义 |
|------|------|
| **ID** | 任务编号，便于 PR / Issue 引用 |
| **验收** | 完成定义（DoD） |
| **依赖** | 须先完成的任务 |
| **估时** | 单人原型改动粗估 |

**维护约定**：改 `02-app.js` 为主；`app.js` 若仍存在仅作备份，不必双改。改 HTML 后必须 `python3 prototype/build.py`。

---

## P0 — 主路径闭环（Demo 必做）

### P0-01 · 修复 `confirmAIReview` 并跳转评审工作台

| 项 | 内容 |
|----|------|
| **问题** | `confirmAIReview()` 查询 `#stage-ai`（DOM 不存在），在 `ai-review` 页点击后不切页；`switchStage('legal')` 只作用于隐藏的 `review-workspace`。 |
| **文件** | `prototype/js/02-app.js`（`confirmAIReview`，约 L1357） |
| **文件** | `prototype/pages/page-ai-review.html`（按钮区，约 L63–66） |

**改动步骤**

1. **校验逻辑改为报告页内**（二选一，推荐 A）  
   - **A（推荐）**：统计 `#page-ai-review .risk-item.high` 是否均已「确认」——在点击「确认审查结论」前，要求高风险项至少展开/或增加每项「已阅」勾选（`data-reviewed="1"`）；未满足则 `showToast` 并 `return`。  
   - **B（最小）**：仅确认弹窗 `confirm('确认进入法务评审？')`，无 DOM 依赖。

2. **写入状态并跳转**  
   ```js
   const no = sessionStorage.getItem('current_contract_no');
   sessionStorage.setItem('ai_review_confirmed', no || '1');
   showToast('✅ 审查结论已确认，进入法务评审');
   switchPage('review-workspace');
   applyWorkspaceFlowTabs(sessionStorage.getItem('current_contract_flow') || 'standard');
   switchStage('legal');
   ```
   - 将工作台「AI 初筛」Tab 标为 `completed`（`document.querySelector('[data-stage=ai]')?.classList.add('completed')`），**不要**再依赖 `#stage-ai` 面板。

3. **（可选）** 删除或注释对 `#stage-ai .review-panel` 的查询，避免后续误用。

**HTML（P0-01 配套）**

- 在 `page-ai-review.html` 增加主按钮（与 P1-04 可合并）：  
  `onclick="confirmAIReview()"` 文案改为 **「提交法务评审 →」**，原「确认审查结论」可保留为次要按钮或合并为一个。

**验收**

- [ ] 在 `ai-review` 页点击确认后，**活动页变为** `review-workspace`，法务 Tab 为 active。  
- [ ] 不再出现「还有 N 项 AI 标记未处理」且 N 来自不存在的 `#stage-ai`。  
- [ ] `current_contract_flow` 为 simple 时，财务/高管 Tab 仍被 `applyWorkspaceFlowTabs` 隐藏。

**依赖**：P0-03（标题随合同号刷新更佳，非阻塞）  
**估时**：1–2h

---

### P0-02 · 提交合同时写入 `current_contract_no`

| 项 | 内容 |
|----|------|
| **问题** | `submitContract()` 只写 `current_contract_flow`，未写合同号，导致后续 AI/详情/工作台无法绑定新单。 |
| **文件** | `prototype/js/02-app.js`（`submitContract`，约 L625 后） |

**改动**

```js
sessionStorage.setItem('current_contract_no', contractNo);
sessionStorage.setItem('current_contract_flow', flowType);
```

在 `showFlowMatchModal` / `switchPage('ai-review')` **之前**写入。

**验收**

- [ ] 新建提交后，`sessionStorage.current_contract_no` 等于新生成的 `CTR-…`。  
- [ ] 进入 `ai-review` 后，P0-03 的标题可显示该编号（实现 P0-03 后验证）。

**依赖**：无  
**估时**：15min

---

### P0-03 · 合同上下文渲染 `renderContractContext(no)`

| 项 | 内容 |
|----|------|
| **问题** | `showContractDetail` 已写 session，但 `contract-detail` / `ai-review` / `review-workspace` 文案写死 `CTR-20240115-0001`。 |
| **文件** | `prototype/js/02-app.js`（新增函数 + 调用点） |
| **文件** | `prototype/pages/page-contract-detail.html` |
| **文件** | `prototype/pages/page-ai-review.html` |
| **文件** | `prototype/pages/page-review-workspace.html` |

**改动步骤**

1. **新增** `getActiveContract()`  
   ```js
   function getActiveContract() {
     const no = sessionStorage.getItem('current_contract_no');
     return contracts.find((c) => c.no === no) || contracts.find((c) => c.no === 'CTR-20240115-0001') || contracts[0];
   }
   ```

2. **新增** `renderContractContext(contract)`（或传 `no`）更新以下 **id**（须在 HTML 中补上）：

   | 页面 | 建议元素 id | 更新字段 |
   |------|-------------|----------|
   | `contract-detail` | `#detail-contract-title` | `no + ' ' + name` |
   | | `#detail-status-tags` | statusName / risk tag |
   | | `#detail-meta-grid` 内子项 | 金额、相对方、类型、日期（可用 `data-field` + 循环） |
   | `ai-review` | `#ai-review-title` | 报告标题（替换 card-title 内静态文案） |
   | | `#ai-review-flow-tag` | flowTypeName |
   | `review-workspace` | `#workspace-contract-head` | 原文区标题行 |
   | | `#workspace-contract-meta` | 版本/提交人/风险分（可用合同字段或占位） |

3. **调用点**  
   - `showContractDetail(no)` 末尾：`renderContractContext(contracts.find…)`  
   - `switchPage` 中：`if (pageId === 'ai-review' \|\| pageId === 'contract-detail' \|\| pageId === 'review-workspace') renderContractContext(getActiveContract());`  
   - `submitContract` 跳转 AI 前：`renderContractContext(contract)`  
   - `openMessageDetail`（P1-06）跳转后同上  

4. **HTML**：将三页中写死的 `CTR-20240115-0001 服务器采购合同` 包进带 id 的 `<span>`，勿删演示正文结构。

**验收**

- [ ] 列表点「查看」不同合同，详情标题与金额/相对方随 `contracts` 变化。  
- [ ] 提交新合同后，AI 报告标题为新编号。  
- [ ] 从消息点进 AI（P1-06 后）标题与 `data-contract` 一致。

**依赖**：P0-02  
**估时**：3–4h

---

### P0-04 · 评审中心看板 → 评审工作台

| 项 | 内容 |
|----|------|
| **问题** | `review-center` 看板卡无点击入口，与 `review-workspace` 断裂。 |
| **文件** | `prototype/pages/page-review-center.html`（看板 `.kanban-card`，约 L30–47 及后续列） |
| **文件** | `prototype/js/02-app.js`（新增 `openReviewWorkspace(contractNo)`） |

**改动步骤**

1. **JS 新增**  
   ```js
   function openReviewWorkspace(contractNo) {
     sessionStorage.setItem('current_contract_no', contractNo);
     const c = contracts.find((x) => x.no === contractNo);
     if (c?.flowType) sessionStorage.setItem('current_contract_flow', c.flowType);
     switchPage('review-workspace');
     applyWorkspaceFlowTabs(sessionStorage.getItem('current_contract_flow') || 'standard');
     switchStage('legal');
     if (typeof renderContractContext === 'function') renderContractContext(c);
   }
   ```

2. **HTML**：每张任务卡增加  
   - `onclick="openReviewWorkspace('CTR-20240115-0001')"`（按卡上合同号）  
   - 卡内按钮：**「开始评审」** `btn btn-primary btn-sm`，`event.stopPropagation()` 防冒泡（可选）  
   - `cursor:pointer` + `title="进入评审工作台"`

3. **冲突区**「处理/升级」按钮可继续调 `resolveConflict` / `escalateConflict`，不冲突。

**验收**

- [ ] 从评审中心任一点「待评审」卡进入 `review-workspace`，且 `current_contract_no` 正确。  
- [ ] 侧栏「评审工作台」与看板入口行为一致。

**依赖**：P0-03（推荐）  
**估时**：1h

---

### P0-05 · 下钻页返回与审批历史联动（合同详情）

| 项 | 内容 |
|----|------|
| **问题** | `contract-detail` 无返回；用户从下钻页无法回到列表/来源页。 |
| **文件** | `prototype/pages/page-contract-detail.html`（card-header 前） |
| **文件** | `prototype/js/02-app.js`（`backFromContractDetail()`） |

**改动**

1. 详情页顶栏增加：  
   `<button class="btn btn-outline btn-sm" onclick="backFromContractDetail()">← 返回</button>`

2. **JS**  
   ```js
   function backFromContractDetail() {
     const ret = sessionStorage.getItem('approval_history_return') || 'contracts';
     switchPage(ret === 'contract-detail' ? 'contracts' : ret);
   }
   ```
   - `showContractDetail` 已设 `approval_history_return`（当前为 `'contracts'`）；若从 `dashboard` 进入，应在 `showContractDetail` 增加参数或根据 `document.querySelector('.page.active')` 写入 return（与 `showApprovalHistory` 一致）。

3. **增强** `showContractDetail(no, returnPage?)`：  
   `sessionStorage.setItem('approval_history_return', returnPage || activePageId)`。

**验收**

- [ ] 从合同列表进详情 → 返回 → 回到列表。  
- [ ] 从看板进详情 → 返回 → 回到 dashboard。

**依赖**：无  
**估时**：45min

---

## P1 — 体验与假交互修复

### P1-01 · 纠正四页「查询」误绑 `filterContracts`

| 项 | 内容 |
|----|------|
| **问题** | 用印/归档/相对方/审计的查询按钮 `onclick="filterContracts()"`，在无 `#contract-search` 时无效或误操作合同列表逻辑。 |
| **文件** | `page-seal.html`、`page-archives.html`、`page-counterparties.html`、`page-audit.html` |
| **文件** | `02-app.js`（新增 4 个 filter 函数） |

**改动步骤**

1. 各页 `search-bar` 控件增加 id，例如：

   | 页面 | 搜索框 id | 下拉 id |
   |------|-----------|---------|
   | seal | `seal-search` | `seal-status-filter` |
   | archives | `archive-search` | `archive-status-filter` |
   | counterparties | `cp-search` | `cp-status-filter` |
   | audit | `audit-search` | `audit-action-filter` |

2. **JS 新增**（原型级：过滤当前页 `tbody tr` 的 `textContent` + `data-status`）  
   - `filterSealList()` / `resetSealFilter()`  
   - `filterArchiveList()` / `resetArchiveFilter()`  
   - `filterCounterpartyList()` / `resetCounterpartyFilter()`  
   - `filterAuditLog()` / `resetAuditFilter()`  

3. HTML 按钮改为对应 `onclick`；归档页保留 `filterContractsByDate` 仅作用于 `#page-archives tbody`（修正函数内选择器，勿调用 `filterContracts`）。

**验收**

- [ ] 四页点击「查询」有 Toast 或行隐藏，**不**触发 `#page-contracts` 表格变化。  
- [ ] `_click-test.mjs` 中若按 `filterContracts()` 点审计/用印，需改为点新函数或跳过（见 P1-01 测试）。

**估时**：2–3h

---

### P1-02 · 统一相对方新建入口

| 项 | 内容 |
|----|------|
| **问题** | 创建页用 `modal-new-counterparty`（`saveNewCounterparty`），相对方页用 `modal-add-counterparty`（`createCounterparty` 取 `input[name=name]` 但 HTML 无 `name`）。 |
| **文件** | `partials/modals.html`、`page-create.html`、`page-counterparties.html`、`02-app.js` |

**改动步骤（推荐：保留简版模态，扩展字段）**

1. **统一入口**：`page-counterparties` 的「+ 新增」改为 `showNewCounterpartyModal()`（与 create 一致）。  
2. **修复** `createCounterparty()`：改为读 `#new-counterparty-name` / `#new-counterparty-credit`，或给 `add-counterparty` 表单项补 `name` 属性并只保留一个模态。  
3. **删除或废弃** `modal-add-counterparty`（若合并），避免双份维护。  
4. 保存后：`localStorage.counterparties` 追加 + 创建页下拉 `filterCounterparties` 可刷新的静态列表（可选读 storage）。

**验收**

- [ ] 相对方页「保存」后 Toast 成功，列表新增一行（DOM 插入或刷新）。  
- [ ] 创建页「新建相对方」与相对方页行为一致，信用代码校验仍可用。

**估时**：2h

---

### P1-03 · 修订工作台：说明、进度、提交去向、草稿

| 项 | 内容 |
|----|------|
| **问题** | `submitRevision` 校验 `textarea` 但页面无该字段；进度写死 1/4；`saveDraftCreate` 找 `#contract-create-form` 失败；提交后去 `review-center` 不符合「再进 AI/评审」文档。 |
| **文件** | `page-revision-workspace.html`、`02-app.js` |

**改动步骤**

1. **HTML** 底栏上方增加：  
   ```html
   <div class="form-group" style="margin-top:12px">
     <label class="form-label">修订说明 *</label>
     <textarea class="form-input" id="revision-summary" rows="3" placeholder="请说明本次修订要点…"></textarea>
   </div>
   ```

2. **`submitRevision`**  
   - 校验 `#revision-summary`  
   - `revision-submitted` 写入 `sessionStorage.current_contract_no`  
   - 跳转：`switchPage('ai-review')` 或 `openReviewWorkspace(no)`（与 [workflow-vs-review.md](../design/workflow-vs-review.md) §3 一致，建议 **ai-review** 表示重跑初筛）

3. **`saveDraftRevision()`** 替代修订页上的 `saveDraftCreate`：  
   `localStorage['revision-draft-' + no] = JSON.stringify({ summary, items, savedAt })`

4. **`updateRevisionProgress()`**：在 `acceptRevision` / `rejectRevision` / `enableInlineEdit` 成功回调中调用，更新「已处理/总数」与 progress bar width。

**验收**

- [ ] 未填修订说明无法提交。  
- [ ] 接受/拒绝建议后进度数字变化。  
- [ ] 重新提交后进入 `ai-review`（或工作台，与产品确认二选一并在文档注明）。

**估时**：2–3h

---

### P1-04 · AI 审查页主 CTA 与职责文案

| 项 | 内容 |
|----|------|
| **问题** | 用户不知「确认」后去哪；与 `review-workspace` 内 AI Tab 职责重叠。 |
| **文件** | `page-ai-review.html`、`page-review-workspace.html`（Tab 文案）、`02-app.js` |

**改动**

1. 报告页 header 按钮顺序：  
   **主**：`提交法务评审 →`（`confirmAIReview`）  
   **次**：重新审查、导出 PDF  

2. 门禁卡片下增加一行说明（12px 灰字）：  
   「本页为 AI 初筛只读报告；法务条款评审请在提交后于「评审工作台」处理。」

3. **工作台** `data-stage=ai` Tab：  
   - **方案 A**：`display:none` 并从 Tab 栏移除（AI 只在独立页）  
   - **方案 B**：保留 Tab，点击时 `switchPage('ai-review')` + Toast「AI 初筛在审查报告页完成」

**验收**

- [ ] 新用户 Demo 路径：提交 → AI 报告 → 明显主按钮 → 工作台法务。  
- [ ] 工作台不再出现无内容的 AI stage 面板。

**依赖**：P0-01  
**估时**：1h

---

### P1-05 · 消息跳转写入合同上下文

| 项 | 内容 |
|----|------|
| **问题** | `openMessageDetail` 已有 `data-contract`，但未 `setItem('current_contract_no')`，目标页标题仍静态。 |
| **文件** | `02-app.js`（`openMessageDetail`，约 L1522） |

**改动**

```js
sessionStorage.setItem('current_contract_no', contractNo);
const c = contracts.find((x) => x.no === contractNo);
if (c?.flowType) sessionStorage.setItem('current_contract_flow', c.flowType);
setTimeout(() => {
  switchPage(targetPage);
  if (typeof renderContractContext === 'function') renderContractContext(c);
}, 300);
```

**验收**

- [ ] 点「新审批待办」进 `approvals` 后，再进 AI/详情时标题为消息内合同号（配合 P0-03）。

**依赖**：P0-03  
**估时**：30min

---

### P1-06 · 审批配置阈值与 `submitContract` 对齐

| 项 | 内容 |
|----|------|
| **问题** | `config` 表格与 `workflow-vs-review` 一致，但 `submitContract` 硬编码 `100000` / `1000000`。 |
| **文件** | `02-app.js`、`01-data.js`（可选常量）、`page-config.html` |

**改动步骤**

1. 在 `01-data.js` 增加 `FLOW_THRESHOLDS`（采购/销售/劳务，与 config 表一致）。  
2. 抽取 `resolveFlowType(contractType, amountNum)`，`submitContract` 调用。  
3. `saveConfigEdit()` 将编辑结果写入 `localStorage.flow_thresholds`（JSON），`resolveFlowType` 优先读 storage。  
4. Demo 说明：config 页保存后 Toast「已更新，新建合同将按新阈值匹配流程」。

**验收**

- [ ] 采购 9 万 → simple，150 万 → standard，110 万 → special（与表一致）。  
- [ ] 修改 localStorage 阈值后，再提交新合同流程类型变化。

**估时**：2h

---

### P1-07 · 用印确认传参与归档引导（可选增强）

| 项 | 内容 |
|----|------|
| **问题** | `confirmSealAction()` 无参；`executiveApprove` 后未引导归档。 |
| **文件** | `page-seal.html`、`02-app.js`（`confirmSealAction`, `executiveApprove`） |

**改动**

1. HTML：`onclick="confirmSealAction('CTR-20240115-0001')"`  
2. JS：更新 `contracts` 中对应条目的 `status`/`statusName`（示意），Toast 含「前往归档台账」按钮或 2s 后 `switchPage('archives')`（可选）。  
3. `executiveApprove` 成功后可 `switchPage('seal')` 并 `setItem('current_contract_no', …)`。

**验收**

- [ ] 用印后该行状态变为已用印（DOM 或重新 render 列表）。  
- [ ] 高管通过后能进入用印页（手工路径可演示）。

**估时**：1–2h

---

## 任务总览与建议顺序

```text
P0-02 → P0-03 → P0-01 → P0-04 → P0-05
         ↓
P1-05 → P1-04（依赖 P0-01）
P1-01、P1-02、P1-03、P1-06、P1-07 可并行
```

| ID | 优先级 | 估时 | 阻塞 Demo |
|----|--------|------|-----------|
| P0-01 | P0 | 1–2h | 是 |
| P0-02 | P0 | 0.25h | 是 |
| P0-03 | P0 | 3–4h | 是 |
| P0-04 | P0 | 1h | 是 |
| P0-05 | P0 | 0.75h | 中 |
| P1-01 | P1 | 2–3h | 否 |
| P1-02 | P1 | 2h | 否 |
| P1-03 | P1 | 2–3h | 中 |
| P1-04 | P1 | 1h | 中 |
| P1-05 | P1 | 0.5h | 否 |
| P1-06 | P1 | 2h | 否 |
| P1-07 | P1 | 1–2h | 否 |

**P0 合计**：约 6–9h  
**P1 合计**：约 11–15h  

---

## 手工 Demo 验收路径

### 路径 A — 标准流程（评审驱动）

1. 角色：**业务员** → `create` 填金额 150 万 → 提交  
2. `flow-match` → `ai-review` → **提交法务评审**（P0-01）  
3. `review-workspace` 法务 Tab 处理 AI 标记 → 通过  
4. 角色切 **财务** → 财务 Tab → 通过  
5. 角色切 **法务/高管** → 高管通过 → `seal` 用印（P1-07）→ `archives`  

### 路径 B — 退回修订

1. `review-workspace` → 退回修改 → `revision-workspace`  
2. 填写修订说明（P1-03）→ 接受 2 条 → 重新提交 → `ai-review`  
3. 再次 P0-01 进入法务评审  

---

## 测试与构建

```bash
cd prototype && python3 build.py
node _click-test.mjs
```

**点击测试注意（P1-01 后需更新）**

- `_click-test.mjs` 中对 `page-seal` / `page-audit` 等使用 `button[onclick="filterContracts()"]` 的用例，改为新函数名或改为「仅打开页面不断言筛选」。  
- 新增用例（可选）：`confirmAIReview` 后 `#page-review-workspace.active`；`openReviewWorkspace` 从 center 进入。

---

## P2 — 体验增强（2026-05-19 已实施）

| ID | 任务 | 状态 | 主要文件 |
|----|------|------|----------|
| **P2-01** | 看板统计卡 + 快捷入口可点击 | ✅ | `page-dashboard.html`、`goArchivesExpiring()` |
| **P2-02** | 顶栏「严格权限」开关 | ✅ | `shell.html`、`toggleStrictRbacMode()`、`switchRole()` |
| **P2-03** | 审计日志动态渲染 | ✅ | `renderAuditLog()`、`#audit-log-body` |
| **P2-04** | 相对方新增统一简版模态 | ✅ | `page-counterparties.html` → `showNewCounterpartyModal()` |

### P2-02 验收

- [ ] 勾选「严格权限」后，法务角色侧栏无「待办审批」等项  
- [ ] 取消勾选后恢复 17 项全展示 + `nav-restricted` 半透明  

### P2-03 验收

- [ ] 提交新合同后，审计页出现「提交合同」记录（`addAuditLog`）  
- [ ] 筛选「创建/审批」有效  

---

## 附录：P2+ 已完成

| 项 | 说明 | 状态 |
|----|------|------|
| 合同详情统一为下钻页（D10） | 移除 `modal-contract-detail`；`showModal('contract-detail')` → `showContractDetail` | ✅ |
| 样例合同编号对齐 | 看板/消息/归档/评审中心与 `01-data.js` 中 `defaultContracts` 一致；看板「年度安保」可下钻详情 | ✅ |
| 逐页结构审计 | `prototype/_page-audit.mjs`（div 平衡、非嵌套、标题映射）；见 `prototype/README.md` 回归测试 |
| 完整 E2E 测试 | `_e2e-test.mjs` / `_run-tests.mjs`：P0 主路径、20 页、RBAC、Demo、数据一致性（150+ 项） | ✅ |

---

## 实施状态总览

| 批次 | 状态 |
|------|------|
| P0（5 项） | ✅ 已完成 |
| P1（7 项） | ✅ 已完成 |
| P2（4 项） | ✅ 已完成 |

---

## 变更记录

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.2 | 2026-05-19 | 样例编号对齐；`_page-audit.mjs`；评审工作台闭合标签修复 |
| 1.1 | 2026-05-19 | P0/P1 落地；P2 看板/RBAC/审计/相对方 |
| 1.0 | 2026-05-19 | 初版：P0×5 + P1×7 可执行清单 |
