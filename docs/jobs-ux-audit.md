# 乔布斯标准 — 全站 UX 评审报告

> 版本：1.0.0 | 日期：2026-05-27  
> 评分：1–5（5 = 打开即知该做什么、零演示污染、全站一致）  
> 整改状态：Done = 本迭代已落地 | Pending = 待后续

## 评审原则

| 原则 | 问句 |
|------|------|
| Focus | 3 秒内能否回答「我现在该做什么」？ |
| Simplicity | 能否再删 30% 控件而不损业务？ |
| End-to-end | 能否不切角色、不读文档走完链路？ |
| It just works | 空态/错误是否给出下一步？ |
| Say no | 是否有非生产元素？ |
| Details | 术语/状态/布局是否全站一致？ |
| Delight | 关键动作是否有清晰反馈？ |

## 页面评分矩阵

| 页面 | 路由 | 预审 | 整改后 | Top3 问题 | 状态 |
|------|------|:----:|:------:|-----------|------|
| LoginView | `/login` | 3 | 4 | 演示快捷登录冗余；双入口切角色 | Done |
| AppLayout | — | 2 | 4 | 演示角色下拉；17 项侧栏过载 | Done |
| DashboardView | `/` | 3 | 4 | 无 Hero 待办；布局与 page-card 不一致 | Done |
| MessagesView | `/messages` | 4 | 4 | 渠道列略密；SLA 仅背景色 | Done |
| CreateContractView | `/create` | 2 | 4 | 四模式 Tab 认知负荷；演示预填 | Done |
| ContractListView | `/contracts` | 3 | 3 | 过滤器过多；行内多 link；**草稿删除** | Done |
| TemplatesView | `/templates` | 4 | 4 | 行内多操作；switchRole 已移除 | Done |
| AiReviewView | `/ai-review/:id?` | 2 | 4 | MLX/矩阵并列；工具栏平权 | Done |
| ClauseCompareHubView | `/clause-compare` | 4 | 4 | 引导清晰 | Done |
| ClauseCompareView | drilldown | 4 | 4 | diff 纯文本 | Pending |
| ReviewCenterView | `/review-center` | 4 | 4 | 合并待办+历史 Tab | Done |
| ReviewWorkspaceView | `/review-workspace/:id?` | 2 | 4 | DEMO 步骤；自动切角色 | Done |
| ReviewHistoryView | `/review-history` | 4 | 4 | 仍可通过路由访问 | Done |
| ApprovalsView | `/approvals` | 3 | 3 | 流程 ID 暴露 | Pending |
| SealView | `/seal` | 3 | 4 | 隐式合同 #；switchRole | Done |
| ArchivesView | `/archives` | 3 | 4 | DEMO-02 占主视觉 | Done |
| CounterpartiesView | `/counterparties` | 3 | 4 | 测试拒绝按钮 | Done |
| ConfigView | `/config` | 3 | 4 | DEMO-03 折叠区 | Done |
| UsersView | `/users` | 3 | 4 | 角色 ID 筛选 | Done |
| AuditView | `/audit` | 4 | 4 | 动作自由文本筛选 | Done |
| ContractDetailView | drilldown | 2 | 4 | 9+ 区块；技术字段；**草稿删除** | Done |
| ApprovalHistoryView | drilldown | 4 | 4 | 与详情 Steps 重复 | Pending |
| RevisionWorkspaceView | drilldown | 3 | 4 | 模拟法务退回 | Done |

## 共享组件

| 组件 | 预审 | 整改后 | 说明 | 状态 |
|------|:----:|:------:|------|------|
| ContractContextBar | 3 | 4 | 五按钮 → 主 CTA + 更多 | Done |
| StatusTag | 3 | 4 | 补全 in_review/returned 等 | Done |
| AiGateSummary | 3 | 3 | 术语待业务化 | Pending |
| AiChecklistMatrix | 3 | 3 | 默认折叠于 AI 页 | Done |

## 验收记录

- [x] 演示 UI：`grep -R "DEMO-\|演示角色\|模拟法务\|测试拒绝" frontend/src` 无命中
- [x] 侧栏 17 → 15（移除评审工作台、评审历史独立项，合并至评审中心 Tab）
- [x] E2E `switchRole` 改为 API 多账号登录
- [x] 全量 smoke + demo/ux E2E（见 CI 或本地 `npx playwright test`）

## 截图占位

| 页面 | 整改前 | 整改后 |
|------|--------|--------|
| Dashboard Hero | `docs/screenshots/jobs/dashboard-before.png` | `docs/screenshots/jobs/dashboard-after.png` |
| Create 向导 | — | `docs/screenshots/jobs/create-wizard.png` |
| AI 报告三层 | — | `docs/screenshots/jobs/ai-review-layers.png` |
| 合同详情 Tab | — | `docs/screenshots/jobs/contract-detail-tabs.png` |
