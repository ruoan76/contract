# 数据字典 — 类型与枚举

> 版本：1.1.0 | 日期：2026-05-18 | 关联 [DESIGN_STATUS.md](./DESIGN_STATUS.md)  
> AI 细分类与 15 风险标签见 [contract-review-pro-seeds.md](../reference/contract-review-pro-seeds.md)。

---

## 1. 合同类型 `contract_type`

用于合同主表、列表筛选、流程匹配。

| 值 | 中文 | 说明 |
|----|------|------|
| `purchase` | 采购合同 | |
| `sales` | 销售合同 | |
| `labor` | 劳务合同 | |
| `nda` | 保密协议 | |
| `cooperation` | 合作合同 | 扩展类型 |
| `legal-standard` | 法务制式合同 | 扩展类型 |
| `other` | 其他 | |

**AI 审查配置（扩展，不进主表枚举）**：

| 字段 | 说明 |
|------|------|
| `ai_profile_key` | 映射上游 30 类合同审查配置（默认见 seeds 文档 §4） |
| `ai_review_depth` | `quick` / `standard` / `deep`，对应审查 Session 深度 |

---

## 2. 模板分类 `template_category`

用于模板库，与合同类型大体对应但可更少。

| 值 | 中文 | PRD 标准五类 |
|----|------|-------------|
| `purchase` | 采购 | ✅ |
| `sales` | 销售 | ✅ |
| `labor` | 劳务 | ✅ |
| `confidential` | 保密 | ✅ |
| `nda` | NDA | ✅ |

模板编码示例：`PUR-001`、`SAL-001`、`NDA-001`。

---

## 3. 流程类型 `flow_type`

| 值 | 中文 | 说明 |
|----|------|------|
| `simple` | 简易流程 | 审批 + 法务快审 |
| `standard` | 标准流程 | 完整评审链 |
| `special` | 特殊流程 | 含董事会 |

详见 [workflow-vs-review.md](./workflow-vs-review.md)。

---

## 4. 主状态 `contracts.status`

见 [contract-status-dictionary.md](./contract-status-dictionary.md) §1。

---

## 5. 审批子状态 `contracts.approval_status`

见 [contract-status-dictionary.md](./contract-status-dictionary.md) §2。

---

## 6. 风险等级 `risk_level`

| 值 | 中文 |
|----|------|
| `low` | 低风险 |
| `medium` | 中风险 |
| `high` | 高风险 |

---

## 7. AI 风险标签 `risk_label_id`（种子数据）

来源：上游 `risk_labels.csv`（L01–L15）。与 `risk_level`、CUAD 并存。

| ID | 名称 | 门类 |
|----|------|------|
| L01 | 合同效力 | 效力与合规 |
| L02 | 格式条款 | 效力与合规 |
| L03 | 主体授权 | 效力与合规 |
| L04 | 关联交易 | 效力与合规 |
| L05 | 合规审查 | 效力与合规 |
| L06 | 价款与支付 | 交易履行 |
| L07 | 交付与验收 | 交易履行 |
| L08 | 违约责任 | 交易履行 |
| L09 | 解除与终止 | 交易履行 |
| L10 | 担保与增信 | 交易履行 |
| L11 | 争议解决 | 争议与文本 |
| L12 | 知识产权与保密 | 争议与文本 |
| L13 | 定义与附件 | 争议与文本 |
| L14 | 文本一致性 | 争议与文本 |
| L15 | 文字与格式 | 争议与文本 |

完整字段与落库见 [contract-review-pro-seeds.md](../reference/contract-review-pro-seeds.md)。

---

## 8. 模板状态 `template.status`

| 值 | 中文 |
|----|------|
| `draft` | 草稿 |
| `pending_publish` | 待发布审批 |
| `published` | 已发布 |
| `archived` | 已废止 |
