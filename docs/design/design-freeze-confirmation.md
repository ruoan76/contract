# 设计冻结确认单

> 项目：合同审批管理平台 V1  
> DESIGN_STATUS 版本：**0.5.0**（冻结签字后升至 **1.0.0**）  
> 冻结日期：________（建议：正式会当日）

**说明**：带「预填」的勾选为设计侧材料就绪；正式会演示确认后由产品改为最终勾选并收集签字。

---

## 确认范围

- [x] [DESIGN_STATUS.md](./DESIGN_STATUS.md)（20 页、V1 边界、冻结决策 D1～D9）— 预填
- [ ] [workflow-vs-review.md](./workflow-vs-review.md) — 定稿待四方签字
- [x] [contract-status-dictionary.md](./contract-status-dictionary.md) — 预填
- [x] [database-design.md](./database-design.md)（含 counterparties）— 预填
- [x] [prd.md](./prd.md)（V1.1 修订）— 预填
- [ ] 原型 `prototype/index.html` + [demo-script-v1.md](./demo-script-v1.md) — 待现场演示确认
- [x] [prd-v1-checklist.md](./prd-v1-checklist.md) 满足率 ≥ 95% — 预填（95%）
- [x] Phase D：[field-dictionary.md](./field-dictionary.md)、[api-page-mapping.md](./api-page-mapping.md)、[permission-matrix.md](./permission-matrix.md) — 预填

预评审记录：[design-freeze-pre-review.md](./design-freeze-pre-review.md)

---

## 演示确认（正式会勾选）

| DEMO | 说明 | 正式会确认 |
|------|------|------------|
| DEMO-01 | 简易流程（8 万采购） | [ ] |
| DEMO-02 | 标准评审（AI + 三 Tab） | [ ] |
| DEMO-03 | 董事会/特殊流程（DEMO-03） | [ ] |
| DEMO-04 | 黑名单（可选） | [ ] |
| DEMO-05 | 退回修订 | [ ] |

---

## 遗留项（≤3 条，须含负责人与目标版本）

| 项 | 负责人 | 目标版本 | 是否阻塞开发 |
|----|--------|----------|--------------|
| 模板发布完整审批流（现状：待发布审批样例行） | 产品 | V1.1 | 否 |
| 审批委托生产实现（现状：原型示意 Toast） | 产品/开发 | V1.1 | 否 |
| 会签节点与并行审批 | 产品 | V2 | 否 |

---

## 签字

| 角色 | 姓名 | 日期 | 签名 |
|------|------|------|------|
| 产品 | | | |
| 法务 | | | |
| 财务 | | | |
| 开发 | | | |

---

## 冻结生效后

1. 将 `DESIGN_STATUS.md` 版本更新为 **1.0.0**，§8 标记「已冻结」。  
2. 在 `workflow-vs-review.md` §6 填写签字。  
3. 开发按 [development-kickoff.md](./development-kickoff.md) 启动。
