# 页面 — API 映射表（V1）

> 版本：1.2.0 | 日期：2026-05-18 | API 规范：[api-spec.md](./api-spec.md) v1.1  
> 页面名称与原型侧栏/顶栏一致，见 [DESIGN_STATUS.md](./DESIGN_STATUS.md) §3.1。  
> 侧栏 17 项 + 下钻 3 项：见 [DESIGN_STATUS.md](./DESIGN_STATUS.md) §3。

| 页面 ID | 页面名称 | 导航 | 主要 API（读） | 主要 API（写） | V1 备注 |
|---------|----------|------|----------------|----------------|---------|
| `dashboard` | 状态看板 | 侧栏 | `GET /api/v1/contracts/dashboard` | — | 执行中/即将到期/已到期 |
| `messages` | 消息中心 | 侧栏 | 规划 `GET /api/v1/notifications` | 规划已读 | 原型 mock |
| `create` | 新建合同 | 侧栏 | `GET /api/v1/counterparties`（规划） | `POST /api/v1/contracts` | 提交后触发 AI |
| `contracts` | 合同列表 | 侧栏 | `GET /api/v1/contracts` | — | 筛选 status/type |
| `contract-detail` | 合同详情 | 下钻 | `GET /api/v1/contracts/{id}` | `PUT`（草稿） | 含版本、流程 |
| `templates` | 模板管理 | 侧栏 | 规划 `GET /api/v1/templates` | 规划 CRUD | V1 可二期 |
| `ai-review` | 审查报告 | 侧栏 | `GET /api/v1/ai-review/{id}/result` | `POST /api/v1/ai-review/review` | 误报反馈规划 |
| `clause-compare` | 条款比对 | 侧栏 | 规划模板 diff API | — | 可合并 AI 模块 |
| `review-center` | 评审中心 | 侧栏 | 待办评审列表（规划） | 冲突仲裁（规划） | |
| `review-workspace` | 评审工作台 | 侧栏 | 合同 + 最新 AI 报告 | 评审意见提交（规划） | 法务/财务/高管 |
| `review-history` | 评审历史 | 侧栏 | 规划按合同聚合 | 导出报告 | |
| `approvals` | 待办审批 | 侧栏 | `GET /api/v1/approvals/pending` | `POST .../approve` | 含退回 |
| `approval-history` | 审批历史 | 下钻 | `GET /api/v1/approvals/{flow_id}/history` | — | 从合同列表/详情进入 |
| `revision-workspace` | 修订工作台 | 下钻 | 评审意见 + 合同版本 | 提交修订（规划） | |
| `seal` | 用印管理 | 侧栏 | 规划 seal 列表 | 用印确认 | |
| `archives` | 归档台账 | 侧栏 | `GET /api/v1/archives/ledger` | `POST .../archive` | 导出 CSV |
| `counterparties` | 相对方管理 | 侧栏 | 规划 counterparties CRUD | 同左 | 含黑名单 |
| `config` | 审批配置 | 侧栏 | `GET` 阈值配置（规划） | `PUT` 配置 | 见 api-spec §6.3 |
| `users` | 用户管理 | 侧栏 | `/api/v1/system/users` | CRUD | |
| `audit` | 审计日志 | 侧栏 | `GET /api/v1/audit` | — | |

---

## 关键用户路径与 API 序列

### 标准流程（DEMO-02）

```text
POST /api/v1/contracts
POST /api/v1/approvals/submit
POST /api/v1/ai-review/review
GET  /api/v1/ai-review/{review_id}/result
POST /api/v1/approvals/{flow_id}/approve  (多节点)
POST /api/v1/archives/{id}/archive
```

### 简易流程（DEMO-01）

```text
POST /api/v1/contracts
POST /api/v1/approvals/submit  (flow_type=simple)
POST /api/v1/ai-review/review
POST /api/v1/approvals/{flow_id}/approve  (部门主管)
-- 法务快审（review API 或 approve 节点 legal）
POST seal / archive
```

---

## 原型仅示意、V1 可不实现 API

| 功能 | 说明 |
|------|------|
| 审批委托 | 原型 Toast 示意 |
| 会签 | V1 不做 |
| 消息飞书卡片 | 通知服务异步，非页面直连 |
