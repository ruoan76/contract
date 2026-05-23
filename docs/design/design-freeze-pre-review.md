# 设计冻结预评审记录

> 版本：1.0.0 | 日期：2026-05-18  
> 性质：**设计侧自检**（非正式四方签字）；正式结论以 [design-freeze-confirmation.md](./design-freeze-confirmation.md) 为准。  
> 依据：[demo-script-v1.md](./demo-script-v1.md)、[prd-v1-checklist.md](./prd-v1-checklist.md)

---

## 1. 会议信息（待填）

| 项 | 内容 |
|----|------|
| 预评审时长 | 建议 30 min |
| 参与人 | 产品：___ 开发：___ 法务（可选）：___ |
| 正式冻结会 | 建议 2h，议程见 [方案 §5.2](../plans/design-freeze-improvement-plan.md#52-正式冻结会) |

---

## 2. 文档材料自检

| 文档 | 版本/状态 | 自检 |
|------|-----------|------|
| DESIGN_STATUS.md | 0.5.0 | ✅ 20 页、与原型 visiblePages/文案对齐 |
| workflow-vs-review.md | 1.0.0 | ✅ 双轨定稿；签字栏待填 |
| contract-status-dictionary.md | 1.0.0 | ✅ 含 Mermaid；采纳 D1 |
| database-design.md | 含 counterparties | ✅ |
| prd.md | V1.1 修订 | ✅ 履约 V2、委托 P1、会签 P2 |
| api-spec.md | v1.1 摘要 | ✅ |
| field-dictionary / api-page-mapping | 1.0.0 | ✅ Phase D 已交付 |
| prd-v1-checklist | 95% | ✅ 1 条待补不阻塞 |
| 4 份 Superseded 审计 | 已标记 | ✅ |

---

## 3. 演示路径自检（对照 demo-script）

在 `prototype/index.html` 本地打开，按角色切换器逐步操作。

| DEMO | 脚本要点 | 原型支撑 | 自检 | 阻断 |
|------|----------|----------|------|------|
| DEMO-01 简易 | 8 万采购 → 流程匹配弹窗 → 主管 → 法务单 Tab → 用印 | `DEMO-01`、`showFlowMatchModal`、简易节点 | ✅ | 无 |
| DEMO-02 标准 | CTR-0007 或 DEMO-05 → AI 65%/52% → 三 Tab 评审 → 归档 | 样例合同、误报/漏报按钮 | ✅ | 无 |
| DEMO-03 特殊 | config 阈值 → 合同列表 DEMO-03 → 审批历史下钻 → 董事会时间线 | `DEMO-03`、`showApprovalHistory` | ✅ | 无 |
| DEMO-04 黑名单 | 相对方黑名单 → 起草警告 | `counterparties` 黑名单 tag | ✅ | 无 |
| DEMO-05 退回 | 退回 → revision-workspace → 再提交 | `confirmApproval` return 跳转 | ✅ | 无 |

**预评审结论**：未发现阻断性死链；建议在正式会由产品现场演示一遍并勾选确认单。

---

## 4. 职责边界（15 min 议题）

见 [workflow-vs-review.md §4](./workflow-vs-review.md#4-职责边界冻结会确认项)。预评审无异议记录；正式会由法务/财务确认。

---

## 5. 建议遗留项（写入确认单，均不阻塞 V1 开发）

| 项 | 负责人 | 目标版本 | 阻塞开发 |
|----|--------|----------|----------|
| 模板发布完整审批流（当前为「待发布审批」样例行） | 产品 | V1.1 | 否 |
| 审批委托生产实现（原型为示意 Toast） | 产品/开发 | V1.1 | 否 |
| 会签节点与并行审批 | 产品 | V2 | 否 |

---

## 6. 阻断项清单

| # | 描述 | 状态 |
|---|------|------|
| — | （预评审未发现） | — |

---

## 7. 下一步

1. 召开正式冻结会，演示 DEMO-01～05。  
2. 填写 [design-freeze-confirmation.md](./design-freeze-confirmation.md) 签字栏。  
3. 同步签署 [workflow-vs-review.md §6](./workflow-vs-review.md#6-确认签字)。  
4. 将 DESIGN_STATUS 升至 **1.0.0（已冻结）** 并更新 §8 冻结状态。  
5. 开发按 [development-kickoff.md](./development-kickoff.md) 启动。
