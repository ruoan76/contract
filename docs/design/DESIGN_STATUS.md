# 设计状态 — 单一真相源（DESIGN STATUS）

> **版本**：1.1.0 | **日期**：2026-05-19 | **阶段**：V1.1 + P2 Stretch 交付  
> **维护规则**：任何影响范围/页面/状态/流程的变更，须更新本文版本号与变更日志。  
> **执行方案**：[design-freeze-improvement-plan.md](../plans/design-freeze-improvement-plan.md) V1.1

---

## 变更日志

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.1.1 | 2026-05-25 | AI 审查能力补强 v1.0：Phase AI-2.5/AI-3 落地（prompt_builder、llm_gateway、completeness、revision_router、rule Batch-1、gates_v2、BM25 RAG、text_segmenter、Celery sync、metrics、生产门禁）；详见 [ai-review-capability-hardening-design.md](../plans/ai-review-capability-hardening-design.md) |
| 1.1.0 | 2026-05-19 | V1.1+P2：模板审批/委托/版本 API/Stretch/5 E2E/DEMO 全绿 |
| 1.0.0-final | 2026-05-19 | V1 全路线：17/17 页、通知事件、模板/条款比对 MVP、E2E CI |
| 1.0.0 | 2026-05-19 | Vue3 Phase 3：review-history、列表分页筛选、高管角色、审批历史时间线、Playwright CI |
| 0.9.0 | 2026-05-19 | Vue3 Phase 2：messages/audit/users、D10 详情、AI 报告、Playwright E2E |
| 0.8.0 | 2026-05-19 | Vue3 前端启动：Vite+Element Plus；DEMO-01~05 页面；Docker/CI |
| 0.7.0 | 2026-05-19 | V1 联调就绪：原型 api 层 + DEMO-01~05 实机；MySQL IT 10/10；GitHub CI；Vue3 延后 V1.1 |
| 0.6.0 | 2026-05-19 | 后端：Phase A–D 完成；165 pytest + 10 integration；RBAC/OpenAPI 就绪 |
| 0.5.3 | 2026-05-19 | 原型：P0/P1/P2 主路径闭环；合同详情统一为下钻页（D10）；严格权限开关 |
| 0.5.2 | 2026-05-18 | AI 种子落地：`backend/seeds/ai_review/` + import 脚本与 generated JSON |
| 0.5.1 | 2026-05-18 | AI：contract-review-pro 种子规划 + ai-review-design §2.3 编排结合 |
| 0.5.0 | 2026-05-18 | 文档与原型对齐：`visiblePages` 与权限矩阵一致、侧栏文案统一、样例数据与字典 |
| 0.4.0 | 2026-05-18 | 导航与权限：17 项侧栏、审批历史下钻、原型全菜单；正式文档迁入 `docs/design/` |
| 0.3.0 | 2026-05-18 | Phase D：字段字典、API 映射、PRD 勾选、权限矩阵、冻结确认单 |
| 0.2.0 | 2026-05-18 | Phase A/B 落实：文档对齐 + 原型 B-1～B-11 等 |
| 0.1.0-draft | 2026-05-18 | 初稿；冻结决策 D1～D7 |

---

## 1. 冻结决策记录

| ID | 决策 | 状态 |
|----|------|------|
| D1 | `status=pending` + `approval_status`，无 `reviewing` | ✅ |
| D2 | 独立 `counterparties` 表 | ✅ 文档已更新 |
| D3 | 简易流程：review-workspace 仅法务 Tab | ✅ [workflow-vs-review.md](./workflow-vs-review.md) |
| D4 | 委托：V1 原型示意；PRD P1 | ✅ |
| D5 | 会签：V1 不做；PRD P2 | ✅ |
| D6 | AI 误报/漏报：演示必做 | ✅ 原型已加 |
| D7 | 不建 page-risk / page-statistics | ✅ |
| D8 | `approval-history` 为合同下钻页，**无侧栏菜单** | ✅ |
| D9 | 原型侧栏 **17 项全展示**；正式环境按 RBAC 隐藏（见 permission-matrix §4） | ✅ |
| D10 | **合同详情仅下钻页** `page-contract-detail`；废弃 `modal-contract-detail`（`showModal('contract-detail')` 重定向） | ✅ |

---

## 2. V1 范围

见 [方案 §九](../plans/design-freeze-improvement-plan.md#九v1-范围边界)。

**后端实现度（2026-05-19）：** Sprint 0–5 + V1.1 完成；`backend/` **176 pytest**（含 IT-12 模板审批、delegate RBAC）。Stretch：**MinIO/Celery/Qwen 实机**待验收；飞书 webhook 已接（需配置 `FEISHU_WEBHOOK_URL`）。

**前端：** `frontend/` Vue3 **V1.1 完成**（草稿/上传/版本/委托/模板审批/5 E2E）；`prototype/` 冻结为设计参考。

**CI：** GitHub Actions 依赖 `pytest-asyncio` + `bcrypt==4.0.1`（见 requirements.txt）。

**AI 范围**：`ai-review-design.md` = 开发蓝图（含 contract-review-pro V3.0 结合 §2.3）；种子数据见 `reference/contract-review-pro-seeds.md`；V1 原型 = 报告 + 置信度 + 误报漏报。

---

## 3. 原型页面清单（20）

### 3.1 侧栏导航（17 项）

与 `prototype/src/shell.html`、`js/02-app.js` 中 `titles` / `pageMap` 一致；`ALL_NAV_PAGES` 见 `js/01-data.js`。

| 分组 | # | 页面 ID | 侧栏文案 | 顶栏标题 |
|------|---|---------|----------|----------|
| 概览 | 1 | `dashboard` | 状态看板 | 状态看板 |
| 概览 | 2 | `messages` | 消息中心 | 消息中心 |
| 起草 | 3 | `create` | 新建合同 | 新建合同 |
| 起草 | 4 | `contracts` | 合同列表 | 合同列表 |
| 起草 | 5 | `templates` | 模板管理 | 模板管理 |
| AI审查 | 6 | `ai-review` | 审查报告 | 审查报告 |
| AI审查 | 7 | `clause-compare` | 条款比对 | 条款比对 |
| 评审 | 8 | `review-center` | 评审中心 | 评审中心 |
| 评审 | 9 | `review-workspace` | 评审工作台 | 评审工作台 |
| 评审 | 10 | `review-history` | 评审历史 | 评审历史 |
| 审批 | 11 | `approvals` | 待办审批 | 待办审批 |
| 签署归档 | 12 | `seal` | 用印管理 | 用印管理 |
| 签署归档 | 13 | `archives` | 归档台账 | 归档台账 |
| 基础数据 | 14 | `counterparties` | 相对方管理 | 相对方管理 |
| 系统 | 15 | `config` | 审批配置 | 审批配置 |
| 系统 | 16 | `users` | 用户管理 | 用户管理 |
| 系统 | 17 | `audit` | 审计日志 | 审计日志 |

### 3.2 下钻页（3 项，无侧栏）

| 页面 ID | 名称 | 入口 |
|---------|------|------|
| `contract-detail` | 合同详情（**全页**，非弹窗） | 看板/合同列表/消息等；顶栏含返回、审批历史、AI 报告、评审工作台 |
| `approval-history` | 审批历史（单合同流程时间线） | 合同列表「审批历史」、详情「审批历史」 |
| `revision-workspace` | 修订工作台 | 评审退回、起草人修订 |

进入下钻页时侧栏 **不高亮** 任意菜单项（`switchPage` 的 `pageMap` 为 -1）。

**合同详情 UX（D10）**：采用全页下钻而非模态框——信息量大（正文、附件、流程、AI 摘要），与 `approval-history` / `revision-workspace` 一致；`sessionStorage.current_contract_no` 驱动 `renderContractContext()` 刷新标题与字段。

### 3.3 权限与原型演示

| 环境 | 侧栏行为 |
|------|----------|
| **正式产品** | 按 [permission-matrix.md](./permission-matrix.md) RBAC **隐藏**无权限菜单 |
| **高保真原型** | **17 项始终展示**；无权限项半透明 + 🔒（`nav-restricted`），仍可点击进入走查 UI |

顶栏角色下拉：切换模拟身份（姓名/部门）与 🔒 标记；勾选 **「严格权限」** 时隐藏无权限菜单（模拟正式 RBAC）。未勾选时 **17 项全展示** + `nav-restricted` 半透明。详见 permission-matrix §3～§4。

**原型 Demo 主路径**（2026-05-19）：`create` 提交 → `ai-review`「提交法务评审」→ `review-workspace` →（可选）`seal` / `archives`；退回 → `revision-workspace` → 再进 `ai-review`。清单见 [prototype-p0-p1-checklist.md](../plans/prototype-p0-p1-checklist.md)。

### 3.4 原型角色与 `visiblePages`（与权限矩阵 §3 一致）

原型顶栏 **6 个模拟角色**（`#role-select`）；PRD 中的 **高管** 不单独占选项，在 `review-workspace` 的 **高管 Tab** 演示。

| 原型 role | 显示职务 | 正式环境可见侧栏（pageId） |
|-----------|----------|---------------------------|
| `drafter` | 业务员 | dashboard, messages, create, contracts, templates, ai-review, archives, counterparties |
| `approver` | 部门主管 | 上列 + clause-compare, approvals, review-center, review-workspace, config |
| `legal` | 法务专员 | dashboard, contracts, ai-review, clause-compare, seal, archives, review-center, review-workspace, templates |
| `finance` | 财务专员 | dashboard, contracts, ai-review, clause-compare, archives, review-center, review-workspace |
| `archivist` | 档案管理员 | dashboard, contracts, seal, archives |
| `admin` | 系统管理员 | 全部 17 项 |

下钻页：`revision-workspace` 列入起草人 `visiblePages`（退回修订入口）；`contract-detail`、`approval-history` 不按角色锁侧栏，随入口进入。

实现与测试：`js/01-data.js` · `switchRole()` · `prototype/_click-test.mjs` 中 `ROLE_PAGES`。

### 3.5 样例数据与字典

| 项 | 约定 |
|----|------|
| 演示合同 | `DEMO-01` / `DEMO-03` / `DEMO-05` + `defaultContracts` 共 17 条 |
| 流程类型 | `flowType`: simple / standard / special（见 [data-dictionary.md](./data-dictionary.md) §3） |
| 合同类型 | `create` 下拉与 [data-dictionary.md](./data-dictionary.md) §1 一致（含 `other`） |
| 存储 | `localStorage['contract_proto']`、草稿 `contract-draft` |

---

## 4. 状态与流程

- [contract-status-dictionary.md](./contract-status-dictionary.md) v1.0.0  
- [workflow-vs-review.md](./workflow-vs-review.md) v1.0.0  
- [data-dictionary.md](./data-dictionary.md)  
- [field-dictionary.md](./field-dictionary.md)  
- [api-page-mapping.md](./api-page-mapping.md)  
- [prd-v1-checklist.md](./prd-v1-checklist.md)（满足率 95%）  
- [permission-matrix.md](./permission-matrix.md)  
- [design-freeze-pre-review.md](./design-freeze-pre-review.md)  
- [design-freeze-confirmation.md](./design-freeze-confirmation.md)  
- [development-kickoff.md](./development-kickoff.md)  
- [demo-script-v1.md](./demo-script-v1.md)

---

## 5. 技术栈（定稿）

MySQL 8 · Redis 7 · MinIO · FastAPI · Vue3（规划）· Qwen（规划）

---

## 6. 落实进度

| 工作包 | 状态 |
|--------|------|
| Phase A 文档 | ✅ 已完成 |
| Phase B 原型 P0 | ✅ 已完成 |
| Phase D 交接文档 | ✅ 已完成 |
| Phase C 预评审材料 | ✅ 已完成（design-freeze-pre-review.md） |
| Phase C 正式会签字 | 材料就绪，待四方现场签字（见 design-freeze-confirmation.md） |

---

## 7. 文档索引

正式设计文档位于 **`docs/design/`**（本目录）；总索引见 [docs/README.md](../README.md)。

### 有效（本目录）

| 文档 | 说明 |
|------|------|
| [README.md](./README.md) | 本目录清单与评审阅读顺序 |
| [prd.md](./prd.md) | 已修订 V1.1（履约/移动/委托会签） |
| [database-design.md](./database-design.md) | 含 counterparties |
| [api-spec.md](./api-spec.md) | v1.1 变更摘要 |
| [prototype/index.html](../../prototype/index.html) | 高保真原型 |

### Superseded

历史审计见 [docs/archive/](../archive/README.md)：

- [comprehensive-design-review.md](../archive/comprehensive-design-review.md)  
- [prototype-completeness-audit.md](../archive/prototype-completeness-audit.md)  
- [p0-p1-completion-report.md](../archive/p0-p1-completion-report.md)

---

## 8. 冻结状态

| 项 | 状态 |
|----|------|
| 设计冻结 | ⏳ 待正式会四方签字（预评审已通过，见 design-freeze-pre-review.md） |
| DESIGN_STATUS | **1.1.0** |
| Dashboard API | `stats` + `executing` / `expiring_soon` / `expired` 三栏（见 api-page-mapping） |
