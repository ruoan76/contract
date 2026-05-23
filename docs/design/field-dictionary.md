# 字段字典 — 原型 / API / 数据库映射

> 版本：1.0.0 | 日期：2026-05-18 | 关联 [DESIGN_STATUS.md](./DESIGN_STATUS.md)

说明：「原型 ID」为 `prototype/index.html` 表单元素；「API」为 `api-spec.md` v1.1；「DB」为 `database-design.md`。

---

## 1. 合同主表 `contracts`

| 原型 ID / 位置 | 标签 | API 字段 | DB 列 | 类型 | 必填 |
|----------------|------|----------|-------|------|------|
| `new-contract-title` | 合同名称 | `title` | `title` | string(200) | 是 |
| `new-contract-type` | 合同类型 | `contract_type` | `contract_type` | enum | 是 |
| `new-contract-counterparty` | 相对方 | `counterparty_name` | `counterparty_name` | string(200) | 是 |
| — | 信用代码（选择后展示） | `counterparty_credit_code` | `counterparty_credit_code` | string(50) | 否 |
| — | 相对方 ID | `counterparty_id` | `counterparty_id` | bigint | 否 |
| `new-contract-amount` | 合同金额 | `amount` | `amount` | decimal | 是 |
| `new-contract-start` | 开始日期 | `start_date` | `start_date` | date | 否 |
| `new-contract-end` | 结束日期 | `end_date` | `end_date` | date | 否 |
| `new-contract-content` | 合同内容/备注 | `content` | —（版本表 `content`） | text | 否 |
| — | 合同编号（系统生成） | `contract_no` | `contract_no` | string(50) | 是 |
| — | 主状态 | `status` | `status` | enum | 是 |
| — | 子阶段 | `approval_status` | `approval_status` | enum | 流程中必填 |
| — | 风险等级 | — | `risk_level` | enum | 否 |
| — | 创建人 | `creator_id` | `creator_id` | bigint | 是 |
| — | 部门 | `department_id` | `department_id` | bigint | 否 |

**合同类型枚举**：见 [data-dictionary.md](./data-dictionary.md) §1。

**提交时流程匹配**（原型计算，非持久字段）：

| 金额条件（示例） | `flow_type` |
|------------------|-------------|
| ≥ 100 万 | `special` |
| 10 万～100 万 | `standard` |
| < 10 万（采购） | `simple` |

---

## 2. 相对方 `counterparties`

| 原型 / 模态框 | 标签 | API（规划） | DB 列 |
|---------------|------|-------------|-------|
| 新建相对方模态 | 名称 | `name` | `name` |
| | 信用代码 | `credit_code` | `credit_code` |
| | 联系人/电话 | `contact_name` / `contact_phone` | 同左 |
| 列表筛选 | 黑名单 | `is_blacklist` | `is_blacklist` |

---

## 3. 审批操作

| 原型操作 | API | 请求体 |
|----------|-----|--------|
| 提交审批 | `POST /api/v1/approvals/submit` | `contract_id`, `flow_type` |
| 通过/拒绝/退回 | `POST /api/v1/approvals/{flow_id}/approve` | `action`: approve \| reject \| return |
| 委托（V1 示意） | — | V1.1 规划 `delegate` |
| 待办列表 | `GET /api/v1/approvals/pending` | — |

---

## 4. AI 审查

| 原型 | API | 说明 |
|------|-----|------|
| 发起审查（提交合同后） | `POST /api/v1/ai-review/review?contract_id=` | 异步 |
| 报告页 | `GET /api/v1/ai-review/{review_id}/result` | |
| 误报/漏报（原型） | 规划 `POST .../feedback` | `type`: false_positive \| false_negative |

| 报告字段 | 存储 |
|----------|------|
| 整体风险等级 | `ai_reviews.overall_risk_level` |
| 评分 | `overall_risk_score` |
| 条款详情 JSON | `clause_reviews` |
| 规则违规 JSON | `rule_violations` |

---

## 5. 用印 / 归档

| 原型页 | 主要 API |
|--------|----------|
| `seal` | `POST /api/v1/seals`（规划） |
| `archives` | `POST /api/v1/archives/{contract_id}/archive`，`GET /api/v1/archives/ledger` |

---

## 6. 用户与系统

| 原型 | API 模块 |
|------|----------|
| `users` | `/api/v1/system/users` |
| `config` | `/api/v1/system/config` 或审批阈值专用 API |
| `audit` | `GET /api/v1/audit` |

---

## 7. 合同版本 `contract_versions`

| 原型（contract-detail 版本表） | DB |
|--------------------------------|-----|
| 版本号 v1/v2 | `version` |
| 变更说明 | `change_description` |
| 文件哈希 | `file_hash` |
