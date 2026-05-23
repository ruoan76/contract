# 原型 ↔ 设计文档 对齐差异报告

> 日期：2025-01-15 | 对比来源：prototype/index.html vs 5 份设计文档

---

## 📊 对齐率总览

| 文档 | 对齐率 | 关键差异项 |
|------|--------|-----------|
| database-design.md | 65% | 9 个缺失字段、2 张表无对应页面 |
| api-spec.md | 70% | 2 个模块无对应页面 |
| prd.md | 75% | 消息中心缺失、导入弹窗缺失 |
| template-design.md | 50% | 模板数 5→10 不足、变量结构缺失 |
| counterparty-design.md | 55% | 模态框缺 5 字段、无黑名单管理页 |
| **综合** | **63%** | **共 15 项需补齐** |

---

## 一、database-design.md → 原型字段对齐

### 1.1 contracts 主表字段对照

| 数据库字段 | 原型合同列表 | 原型合同详情 | 差距 |
|-----------|-------------|-------------|------|
| id | ❌ | ❌ | 原型用 contract_no |
| contract_no | ✅ | ✅ | |
| title | ✅ | ✅ | |
| contract_type | ✅ | ✅ | |
| status | ✅ | ✅ | |
| counterparty_name | ✅ | ✅ | |
| counterparty_credit_code | ❌ | ❌ | **缺失** — 详情页无信用代码 |
| amount | ✅ | ✅ | |
| currency | ❌ | ❌ | **缺失** |
| tax_rate | ❌ | ❌ | **缺失** |
| start_date | ❌ | ✅ | |
| end_date | ❌ | ✅ | |
| sign_date | ❌ | ❌ | **缺失** — DB 有"签署日期" |
| sign_method | ❌ | ❌ | **缺失** |
| seal_record_id | ❌ | ❌ | **缺失** |
| archive_date | ❌ | ❌ | **缺失** — DB 有"归档日期" |
| archive_location | ❌ | ❌ | **缺失** |
| creator_id | ❌ | ❌ | 原型用 creator 名称 |
| department_id | ❌ | ❌ | **缺失** |
| risk_level | ✅ | ✅ | |
| deleted_at | ❌ | ❌ | 软删除，原型无体现 |

### 1.2 contract_versions 表 → 原型

| 数据库字段 | 原型 | 差距 |
|-----------|------|------|
| version | ❌ | **缺失** — 合同详情页无版本历史区域 |
| content / file_path | ❌ | **缺失** |
| file_hash | ❌ | **缺失** |
| change_description | ❌ | **缺失** |

### 1.3 counterparty 表 → 原型

| 数据库/设计字段 | 原型相对方列表 | 原型相对方详情 | 差距 |
|-----------------|---------------|---------------|------|
| company_type (企业类型) | ❌ | ❌ | **缺失** |
| registered_capital | ❌ | ❌ | **缺失** |
| establishment_date | ❌ | ❌ | **缺失** |
| business_scope | ❌ | ❌ | **缺失** |
| contact_email | ❌ | ❌ | **缺失** |

### 1.4 缺失页面（数据库有对应表但原型无页面）

| 表名 | 原型状态 | 优先级 |
|------|---------|--------|
| departments (部门表) | ❌ 无部门管理页 | P1 |
| audit_logs (审计日志) | ❌ 无审计日志页 | P1 |

---

## 二、api-spec.md → 原型对齐

| API 模块 | 原型对应页面 | 对齐 |
|---------|-------------|------|
| /api/v1/contracts | contracts + contract-detail | ✅ |
| /api/v1/approvals | approvals + approval-history | ✅ |
| /api/v1/ai-review | ai-review + review-workspace | ✅ |
| /api/v1/risks | review-center (冲突管理) | ⚠️ 部分覆盖 |
| /api/v1/seals | seal | ✅ |
| /api/v1/archives | archives | ✅ |
| /api/v1/audit | ❌ **无对应页面** | 🔴 |
| /api/v1/statistics | dashboard (仅统计卡) | ⚠️ 部分覆盖 |
| /api/v1/system | config + users | ✅ |

---

## 三、prd.md → 原型对齐

| PRD 要求 | 原型实现 | 差距 |
|---------|---------|------|
| P0: 移动端审批通知 (飞书/企微) | ❌ 无消息中心 | 🔴 P0 缺失 |
| P0: 相对方黑名单管理 | ✅ 相对方列表含黑名单条目 | ✅ |
| P0: 模板偏离高亮 | ❌ 模板预览未展示偏离标记 | 🟡 |
| P1: 批量导入相对方 | ⚠️ 按钮存在但无弹窗 | 🔴 |
| P1: 信用代码格式校验 | ❌ 无校验提示 | 🟡 |

---

## 四、template-design.md → 原型对齐

| 设计项 | 原型 | 差距 |
|--------|------|------|
| 10 个标准模板 | 5 个 | 🔴 **缺 5 个模板** (PUR-003, SAL-002/003, LAB-002, NDA-002) |
| 模板变量结构 (TemplateVariable) | 预览仅文字高亮 | 🟡 变量元信息未展示 |
| 模板状态 (draft/published/archived) | 仅有 草稿/已发布 | 🟡 缺 archived |
| 发布审批流程 | ❌ 未体现 | 🟡 |

---

## 🎯 立即修复清单

### P0 (7 项)

| # | 修复内容 | 改动范围 |
|---|---------|---------|
| 1 | 合同详情页补字段：信用代码、签署日期、归档日期、币种 | HTML |
| 2 | 合同详情页增加版本历史区域 (v1/v2 + diff) | HTML |
| 3 | 新增「消息中心」页面（通知列表+飞书/企微模拟） | HTML+Navi |
| 4 | 新增「审计日志」页面（操作记录表格） | HTML+Navi |
| 5 | 模板列表从 5 扩至 10 个（补齐 PUR/SAL/LAB/NDA） | HTML |
| 6 | 相对方详情模态框补字段（企业类型/注册资本/成立日期/经营范围/邮箱） | HTML |
| 7 | 批量导入相对方弹窗（Excel 上传 + 预览表格） | HTML |

### P1 (3 项)

| # | 修复内容 |
|---|---------|
| 8 | 信用代码格式校验（18位 + 校验位，新建相对方弹窗） |
| 9 | 用户管理页增加角色权限列显示 |
| 10 | 导航组名称统一（与 PRD 模块名对齐） |
