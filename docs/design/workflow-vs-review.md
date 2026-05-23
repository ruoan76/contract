# 审批流与评审流 — V1 定稿说明

> 版本：**1.0.0** | 日期：2026-05-18 | 状态：已定稿（待正式会四方签字）  
> 预评审：[design-freeze-pre-review.md](./design-freeze-pre-review.md)
> 权威记录：[DESIGN_STATUS.md](./DESIGN_STATUS.md) 冻结决策 D3  
> 关联：[workflow-design.md](../reference/workflow-design.md)、[review-process-design.md](../reference/review-process-design.md)

---

## 1. 为什么有两条链

| 概念 | 页面 | 参与者 | 关注点 |
|------|------|--------|--------|
| **审批流** | `approvals` | 部门主管等业务审批人 | 业务是否同意进入下一环节 |
| **评审流** | `review-workspace` | 法务、财务、高管 | 法律风险、财务条款、最终决策 |

V1 **不合并为一套 UI**，通过金额/类型配置选择主路径；简易流程缩短评审深度。

---

## 2. 流程定稿（V1）

### 2.1 标准流程 — 评审驱动

**触发条件**（`config` 金额阈值表，示例）：

- 采购合同：10 万～100 万 → 标准  
- 销售合同：>50 万 → 标准  
- 劳务合同：默认标准  

**路径**：

```text
起草(create) → 提交 → AI 初筛(ai-review)
  → 法务评审(review-workspace / legal)
  → 财务评审(finance，按金额触发)
  → 高管审批(executive，按金额触发)
  → 用印(seal) → 归档(archives)
```

### 2.2 简易流程 — 审批 + 法务快审（D3）

**触发条件**（示例）：

- 采购 ≤10 万、销售 ≤50 万等  

**路径**：

```text
起草 → 提交 → AI 初筛
  → 部门主管(approvals)
  → 法务快审(review-workspace，仅 legal Tab，无财务/高管)
  → 用印 → 归档
```

### 2.3 特殊流程 — 含董事会

**触发条件**：采购 >100 万等（见 `config`）

**路径**：在标准流程高管之后增加 `board_approval` 节点（原型用 `approval-history` 时间线示意）。

---

## 3. 退回与再提交

| 动作 | 入口 | 结果 |
|------|------|------|
| 退回修改 | `review-workspace`、`approvals` | 进入 `revision-workspace` |
| 再提交 | `revision-workspace` | 重新进入 AI（可配置是否重跑，原型勾选示意） |

---

## 4. 职责边界（冻结会确认项）

| 事项 | 负责角色 |
|------|----------|
| 法律条款风险、合规意见 | 法务（`review-workspace`） |
| 付款/预付款/税务 | 财务 |
| 是否批准签署 | 高管 |
| 业务是否立项、部门是否同意 | 部门主管（`approvals`） |
| AI 报告 | 辅助；法务可标记误报/漏报 |

---

## 5. 与原型页面对应

| 阶段 | 原型页面 | 导航 |
|------|----------|------|
| 起草 | `create` | 侧栏 |
| AI | `ai-review` | 侧栏 |
| 部门审批 | `approvals` | 侧栏 |
| 单合同审批轨迹 | `approval-history` | **下钻**（合同列表/详情入口，无侧栏项） |
| 法务/财务/高管 | `review-workspace`（阶段 Tab） | 侧栏 |
| 退回修订 | `revision-workspace` | 下钻 |
| 用印/归档 | `seal`、`archives` | 侧栏 |
| 配置 | `config` | 侧栏 |

侧栏共 **17** 项；原型演示时全部展示，正式环境 RBAC 见 [permission-matrix.md](./permission-matrix.md)。

---

## 6. 确认签字

| 角色 | 姓名 | 日期 | 确认 |
|------|------|------|------|
| 产品 | | | ☐ |
| 法务 | | | ☐ |
| 财务 | | | ☐ |
| 开发 | | | ☐ |
