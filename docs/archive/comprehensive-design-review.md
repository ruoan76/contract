# 合同审批管理平台 — 全量设计文档深度交叉评审报告

> ⚠️ **Superseded**：本文档为历史审计记录，勿作验收依据。请以 [DESIGN_STATUS.md](../design/DESIGN_STATUS.md) 为准。

> 评审日期：2026-05-18 | 文档总数：12 份 | 原型：4,963 行 / 21 页 / 285 个 onclick
> 后端：9 API 文件 / 33 端点 / 7 模型 | 数据库：12 表 | 用户故事：70+

## 一、字段级对齐：PRD ↔ 数据库 ↔ API ↔ 原型

### 1.1 合同主表字段对齐

| 字段 | 数据库设计 | API 规范 | 后端模型 | 原型表单 | 对齐度 |
|------|----------|---------|---------|---------|--------|
| id | ✅ | ✅ | ✅ | ❌ | ⚠️ |
| contract_no | ✅ | ✅ | ✅ | ❌ | ⚠️ |
| contract_name | ❌ | ❌ | ❌ | ❌ | ❌ |
| contract_type | ✅ | ✅ | ✅ | ❌ | ⚠️ |
| counterparty_id | ❌ | ❌ | ❌ | ❌ | ❌ |
| amount | ✅ | ✅ | ✅ | ❌ | ⚠️ |
| currency | ✅ | ✅ | ✅ | ❌ | ⚠️ |
| start_date | ✅ | ✅ | ✅ | ❌ | ⚠️ |
| end_date | ✅ | ✅ | ✅ | ❌ | ⚠️ |
| status | ✅ | ✅ | ✅ | ❌ | ⚠️ |
| creator_id | ✅ | ❌ | ✅ | ❌ | ⚠️ |
| reviewer_id | ✅ | ❌ | ✅ | ❌ | ⚠️ |
| approver_id | ✅ | ❌ | ✅ | ❌ | ⚠️ |
| file_path | ✅ | ✅ | ✅ | ❌ | ⚠️ |
| file_name | ❌ | ❌ | ❌ | ❌ | ❌ |
| file_size | ✅ | ✅ | ✅ | ❌ | ⚠️ |
| file_type | ✅ | ❌ | ✅ | ❌ | ⚠️ |
| template_id | ✅ | ❌ | ❌ | ❌ | ❌ |
| department_id | ✅ | ❌ | ✅ | ❌ | ⚠️ |
| description | ✅ | ✅ | ❌ | ❌ | ⚠️ |
| created_at | ✅ | ✅ | ✅ | ❌ | ⚠️ |
| updated_at | ✅ | ❌ | ✅ | ❌ | ⚠️ |
| deleted_at | ✅ | ❌ | ❌ | ❌ | ❌ |

## 二、审批流程状态机一致性

### 2.1 状态定义对比

| 状态 | workflow-design.md | review-process-design.md | 原型 | 一致性 |
|------|-------------------|------------------------|------|--------|
| AI | ✅ | ✅ | ✅ | ✅ |
| conflict | ❌ | ✅ | ✅ | ⚠️ |
| extra | ❌ | ❌ | ✅ | ❌ |
| match | ❌ | ✅ | ✅ | ⚠️ |
| missing | ❌ | ❌ | ✅ | ❌ |
| 初筛报告 | ❌ | ✅ | ❌ | ❌ |
| 劳动法务组 | ❌ | ✅ | ❌ | ❌ |
| 升级至法务负责人仲裁 | ❌ | ✅ | ✅ | ⚠️ |
| 合同提交 | ❌ | ✅ | ✅ | ⚠️ |
| 存在严重冲突 | ❌ | ✅ | ❌ | ❌ |
| 存在较大冲突 | ❌ | ✅ | ❌ | ❌ |
| 对应财务组 | ❌ | ✅ | ❌ | ❌ |
| 归档 | ✅ | ✅ | ✅ | ✅ |
| 按专长 | ❌ | ✅ | ❌ | ❌ |
| 按部门 | ❌ | ✅ | ❌ | ❌ |
| 最终决策 | ❌ | ✅ | ✅ | ⚠️ |
| 标准流程 | ✅ | ❌ | ✅ | ⚠️ |
| 法务审核 | ✅ | ✅ | ✅ | ✅ |
| 特殊流程 | ✅ | ❌ | ✅ | ⚠️ |
| 生成初筛报告 | ❌ | ✅ | ❌ | ❌ |

## 三、评审流程五阶段详细对比

| 阶段 | review-process-design.md | 原型页面 | 原型函数 | 完成度 |
|------|------------------------|---------|---------|--------|
| AI初筛 | ✅ | ✅ | ✅ | ✅ |
| 法务评审 | ✅ | ✅ | ✅ | ✅ |
| 财务评审 | ✅ | ❌ | ❌ | ❌ |
| 高管审批 | ✅ | ❌ | ❌ | ❌ |
| 评审归档 | ✅ | ✅ | ✅ | ✅ |

## 四、API 端点完整度

API 规范文档端点数：**18**
后端实际端点数：**30**

### 4.1 后端端点列表

| 文件 | 端点 | 方法 |
|------|------|------|
| ai_review.py | /review | POST |
| ai_review.py | /{review_id}/result | GET |
| ai_review.py | /contracts/{contract_id}/latest-review | GET |
| approvals.py | /submit | POST |
| approvals.py | /{flow_id}/approve | POST |
| approvals.py | /pending | GET |
| approvals.py | /{flow_id}/history | GET |
| archives.py | /{contract_id}/archive | POST |
| archives.py | /ledger | GET |
| archives.py | /expired | GET |
| audit.py | / | GET |
| contracts.py | / | POST |
| contracts.py | / | GET |
| contracts.py | /{contract_id} | GET |
| contracts.py | /{contract_id} | PUT |
| contracts.py | /{contract_id} | DELETE |
| risks.py | / | GET |
| risks.py | /{risk_id} | GET |
| risks.py | /{risk_id}/handle | POST |
| risks.py | /statistics | GET |
| seals.py | /apply | POST |
| seals.py | /records/{contract_id} | GET |
| statistics.py | /contracts | GET |
| statistics.py | /approval-efficiency | GET |
| statistics.py | /risk-trend | GET |
| system.py | /users | GET |
| system.py | /roles | GET |
| system.py | /departments | GET |
| system.py | /login | POST |
| system.py | /profile | GET |

## 五、设计文档间交叉引用一致性

| 引用关系 | 源文档 | 目标文档 | 一致性 |
|---------|--------|---------|--------|
| PRD → 数据库 | prd.md | database-design.md | ✅ (12 表 vs PRD 12 模块) |
| PRD → API | prd.md | api-spec.md | ✅ (34 端点 vs PRD 功能) |
| PRD → 用户故事 | prd.md | user-stories.md | ✅ (70+ US vs PRD 模块) |
| 数据库 → 模型 | database-design.md | backend/app/models/contract.py | ✅ (12 表 vs 7 模型) |
| API → 后端 | api-spec.md | backend/app/api/v1/*.py | ❌ (34 端点 vs 33 端点) |
| 评审 → AI审查 | review-process-design.md | ai-review-design.md | ✅ (AI初筛阶段引用) |
| 评审 → 工作流 | review-process-design.md | workflow-design.md | ✅ (审批流程引用) |
| 模板 → PRD | template-design.md | prd.md | ✅ (模板管理模块引用) |
| 相对方 → PRD | counterparty-design.md | prd.md | ✅ (相对方管理模块引用) |
| 移动端 → 工作流 | mobile-approval-design.md | workflow-design.md | ✅ (审批回调引用) |

## 六、关键不一致项（需修正）

| # | 不一致项 | 涉及文档 | 严重程度 | 说明 |
|---|---------|---------|---------|------|
| 1 | 评审阶段数量 | review-process.md vs 原型 | 🔴 高 | 设计文档定义 5 阶段，原型仅实现 3 阶段（缺财务/高管） |
| 2 | 数据库表数量 | database-design.md vs 后端模型 | 🔴 高 | 设计 12 表，后端仅 7 模型，缺 5 张表 |
| 3 | API 端点数量 | api-spec.md vs 后端实现 | 🟡 中 | 规范 34 端点，后端 33 端点，差 1 个 |
| 4 | 状态定义 | workflow.md vs review.md vs 原型 | 🟡 中 | 三处状态定义不完全一致 |
| 5 | 合同类型 | template-design.md vs 原型 | 🟡 中 | 设计 6 种类型，原型仅实现采购合同 |
| 6 | SLA 时间 | review-process.md §3.3 vs 原型 | 🟡 中 | 设计文档有标准/预警/升级时间，原型硬编码 |
| 7 | 角色数量 | PRD vs 数据库 vs 原型 | 🟢 低 | PRD 6 角色，数据库 3 角色表，原型侧边栏按角色显示 |
| 8 | 模板数量 | template-design.md vs 原型 | 🟢 低 | 设计 10+ 模板，原型仅 1 个模板列表页 |

## 七、原型页面功能完整度

原型页面总数：**21**

| 页面 ID | 页面名称 | 按钮数 | JS 函数 | 业务完整度 |
|---------|---------|--------|--------|----------|
| page-ai-review | - | 8 | 4 | ✅ 完整 |
| page-approval-history | - | 0 | 0 | ⚠️ 部分 |
| page-approvals | - | 2 | 1 | ✅ 完整 |
| page-archives | - | 10 | 5 | ✅ 完整 |
| page-audit | - | 4 | 2 | ✅ 完整 |
| page-breadcrumb | - | 4 | 2 | ✅ 完整 |
| page-clause-compare | - | 10 | 5 | ✅ 完整 |
| page-config | - | 2 | 2 | ✅ 完整 |
| page-contract-detail | - | 0 | 0 | ⚠️ 部分 |
| page-contracts | - | 6 | 3 | ✅ 完整 |
| page-counterparties | - | 26 | 13 | ✅ 完整 |
| page-create | - | 2 | 1 | ✅ 完整 |
| page-dashboard | - | 0 | 0 | ⚠️ 部分 |
| page-messages | - | 2 | 1 | ✅ 完整 |
| page-review-center | - | 0 | 0 | ⚠️ 部分 |
| page-review-workspace | - | 12 | 8 | ✅ 完整 |
| page-revision-workspace | - | 6 | 3 | ✅ 完整 |
| page-seal | - | 14 | 7 | ✅ 完整 |
| page-templates | - | 22 | 11 | ✅ 完整 |
| page-title | - | 4 | 2 | ✅ 完整 |
| page-users | - | 27 | 13 | ✅ 完整 |

## 八、综合评分与优先级建议

### 8.1 各维度评分

| 维度 | 评分 | 权重 | 加权分 |
|------|------|------|--------|
| PRD 完整性 | 8/10 | 15% | 1.20 |
| 设计文档深度 | 9/10 | 20% | 1.80 |
| 数据库设计 | 9/10 | 15% | 1.35 |
| API 规范 | 8/10 | 10% | 0.80 |
| 后端实现 | 6/10 | 15% | 0.90 |
| 原型覆盖度 | 7.5/10 | 15% | 1.13 |
| 文档一致性 | 7/10 | 10% | 0.70 |
| **总分** | | **100%** | **7.88/10** |

### 8.2 优先级修复建议

| 优先级 | 修复项 | 工作量 | 影响 |
|--------|--------|--------|------|
| 🔴 P0 | 补齐财务评审工作台 | 3h | 评审流程闭环 |
| 🔴 P0 | 补齐高管终审页面 | 2h | 审批最终决策 |
| 🔴 P0 | 后端补 5 张表模型 | 4h | 数据层完整性 |
| 🟡 P1 | SLA 动态倒计时 | 1.5h | 时效管理体验 |
| 🟡 P1 | 评审冲突交互操作 | 2h | 冲突解决流程 |
| 🟡 P1 | 评审历史独立页 | 2h | 审计追溯 |
| 🟢 P2 | 移动端页面 | 8h | 移动审批 |
| 🟢 P2 | 履约跟踪页面 | 6h | 合同执行 |
| 🟢 P2 | 前端架构文档 | 4h | 开发指导 |
