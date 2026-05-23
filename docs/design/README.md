# 正式设计文档（V1）

> **单一真相源**：[DESIGN_STATUS.md](./DESIGN_STATUS.md)（当前 **0.5.1**）  
> 与原型对齐说明见 DESIGN_STATUS §3、§3.4～§3.5 及 [prototype/README.md](../../prototype/README.md)。  
> 本目录用于**设计冻结、四方评审、开发交接**；请勿将 Superseded 审计放入此目录。

---

## 阅读顺序（评审会推荐）

| 顺序 | 文档 | 说明 |
|------|------|------|
| 1 | [DESIGN_STATUS.md](./DESIGN_STATUS.md) | 范围、20 页、冻结决策 D1～D9 |
| 2 | [prd.md](./prd.md) | 产品需求 V1.1 |
| 3 | [workflow-vs-review.md](./workflow-vs-review.md) | 审批轨 vs 评审轨 |
| 4 | [contract-status-dictionary.md](./contract-status-dictionary.md) | 状态枚举 |
| 5 | [permission-matrix.md](./permission-matrix.md) | RBAC + 原型权限说明 §4 |
| 6 | [demo-script-v1.md](./demo-script-v1.md) | 现场演示脚本 |

---

## 文档清单

### 产品与流程

| 文档 | 说明 |
|------|------|
| [prd.md](./prd.md) | 产品需求文档 |
| [prd-v1-checklist.md](./prd-v1-checklist.md) | PRD P0 验收勾选 |
| [workflow-vs-review.md](./workflow-vs-review.md) | 双轨流程定稿 |
| [contract-status-dictionary.md](./contract-status-dictionary.md) | 合同状态机 |
| [permission-matrix.md](./permission-matrix.md) | 权限矩阵 |
| [demo-script-v1.md](./demo-script-v1.md) | V1 演示脚本 |

### 数据与接口

| 文档 | 说明 |
|------|------|
| [database-design.md](./database-design.md) | 数据库 DDL |
| [data-dictionary.md](./data-dictionary.md) | 枚举与分类 |
| [field-dictionary.md](./field-dictionary.md) | 表单 ↔ DB ↔ API |
| [api-spec.md](./api-spec.md) | REST API v1.1 |
| [api-page-mapping.md](./api-page-mapping.md) | 页面 ↔ API |

### AI 与对齐

| 文档 | 说明 |
|------|------|
| [ai-review-design.md](./ai-review-design.md) | AI 开发蓝图（§2.3 结合 contract-review-pro） |
| [../reference/contract-review-pro-seeds.md](../reference/contract-review-pro-seeds.md) | AI 种子 CSV 落库规划 |
| [design-alignment-requirements.md](./design-alignment-requirements.md) | 设计稿与原型对齐要求 |

### 冻结与开发交接

| 文档 | 说明 |
|------|------|
| [design-freeze-pre-review.md](./design-freeze-pre-review.md) | 预评审记录 |
| [design-freeze-confirmation.md](./design-freeze-confirmation.md) | 正式冻结确认单 |
| [design-change-request-template.md](./design-change-request-template.md) | 设计变更申请模板 |
| [design-freeze-audit-summary.md](./design-freeze-audit-summary.md) | 冻结检查摘要 |
| [development-kickoff.md](./development-kickoff.md) | 开发启动清单 |

---

## 关联目录

- 专题参考：[../reference/](../reference/README.md)
- 实施方案：[../plans/](../plans/)
- 历史审计：[../archive/](../archive/README.md)
- 高保真原型：[../../prototype/](../../prototype/)
