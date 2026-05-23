# 文档-代码对齐报告

> 生成日期：2026-05-23 | **修订：2026-05-19**（Phase A–D 落地后）  
> 目的：识别设计文档与实际代码实现之间的所有不一致，作为文档更新依据。

---

## 2026-05-19 修订摘要（Phase A–D 后）

以下原报告中的 🔴 项**已对齐**：

| 原差异 | 当前状态 |
|--------|----------|
| Alembic 缺失 | ✅ `001→002` 迁移（counterparties、review、notifications） |
| counterparties ORM/API 缺失 | ✅ 模型 + CRUD + 黑名单 + RBAC |
| dashboard 未实现 | ✅ `GET /contracts/dashboard` + IT-07 |
| 待办未按审批人过滤 | ✅ Phase A-2 + IT-06 |
| workflow_service 双轨 | ✅ 已删除，统一 `approval_service` |
| RBAC 未挂 API | ✅ Phase C-1 + IT-08 |

**仍待：** Vue3 `frontend/` 0 代码；Stretch MinIO/Celery；MySQL CI 重跑集成测。

---

## 总览（2026-05-23 初版）

**核心矛盾：文档假设"设计已冻结、代码未开始"，但实际上后端 69 个 Python 文件已实质性开发。**

| 项目 | 文档声称 | 代码实际 | 差异等级 |
|------|---------|---------|---------|
| 后端状态 | "骨架阶段，核心逻辑未实现" | **69 文件，完整业务逻辑** | 🔴 严重 |
| 前端 Vue3 | "空目录，0 代码" | **空目录，0 代码** | ✅ 一致 |
| 设计冻结 | "v0.5.3，待四方签字" | 代码已基于设计大量实现 | 🟡 需更新 |
| JWT 鉴权 | "未实现" | **完整实现** | 🔴 文档过期 |
| AI 审查核心 | "空函数 TODO" | **557 行 + 5 维并行 LLM** | 🔴 文档过期 |
| 审批流程 | "硬编码 5 步" | **JSON 配置驱动 3 种流程** | 🔴 文档过期 |
| Alembic 迁移 | "缺失" | **仍缺失** | ✅ 一致 |

---

## 1. DESIGN_STATUS.md — 全面过时

### 需更新项

| § | 当前内容 | 实际状态 | 建议更新 |
|---|---------|---------|---------|
| §2 范围 | "设计阶段不维护 backend/；冻结后按 api-spec 重建" | **backend/ 已有 69 文件实质性代码** | 更新为"backend/ 已开发约 60% V1 功能" |
| §6 落实进度 | "Phase C 预评审 ✅ / Phase D 交接 ✅" | **远超设计阶段，后端 Sprint 0-4 部分代码已落地** | 新增"代码实现度"状态 |
| §7 文档索引 | "`backend/` 设计阶段不维护" | 已有 `models/`×3, `services/`×10+, `api/v1/`×11, `middleware/`×5, `celery_tasks/`×2 | 改为 "`backend/` 开发进行中" |
| 版本号 | v0.5.3（2026-05-19） | 代码已远超设计阶段 | 升级版本号 + 新增代码状态段 |
| 技术栈 | "Vue3（规划中）" | Vue3 目录已创建 `src/`，子目录齐全但全空 | "Vue3 工程脚手架已创建，待开发" |

---

## 2. development-kickoff.md — 全部失效

### 严重不一致

| 条目 | 文档内容 | 事实 |
|------|---------|------|
| §2 技术栈 | "`backend/` 现有骨架**不沿用**；按 api-spec 重建或移除误导目录" | **backend/ 已是 69 文件实质性业务代码，不是骨架。** 合同 CRUD、审批流、AI 引擎、鉴权、中间件 全部已实现 |
| §4 迭代顺序 | "Sprint 0 工程脚手架 + 认证" | **已完成。** `main.py`, `config.py`, `auth_middleware.py`, `security.py` 全部就位 |
| §4 迭代顺序 | "Sprint 0... 合同 CRUD" | **已完成。** `contract_service.py` CRUD 完整实现 |
| §4 迭代顺序 | "Sprint 1 起草/模板/相对方 + MinIO" | **部分完成。** 相对方表未在 ORM 中创建（缺 `counterparties` 模型），MinIO 上传占位 |
| §4 迭代顺序 | "Sprint 2 审批流引擎" | **已完成。** `approval_service.py` 三流程类型 + JSON 配置 |
| §4 迭代顺序 | "Sprint 4 AI 审查接口" | **大部分完成。** AI 引擎 557 行 + API 端点完整，但 Celery 任务未接真正引擎（mock） |

**建议**：此文件应改写为"开发进度总览"而非"启动清单"。

---

## 3. api-spec.md v1.1 — 多处不一致

### 文档有、代码未实现的端点

| 端点 | 状态 | 说明 |
|------|------|------|
| `GET /api/v1/contracts/dashboard` | ❌ 未实现 | api-spec §6.1 合同状态看板 |
| `POST /api/v1/contracts/{id}/upload` | ⚠️ 占位 | `contract_service.py` 有 `upload_contract_file()` 但 MinIO `upload_file` 调用被注释 |
| `GET/POST /api/v1/counterparties` | ❌ 未实现 | api-spec 标注"V1 开发期补充"，ORM 中也无 Counterparty 模型 |
| `GET /api/v1/risks/{id}/handle` | ❌ 未实现 | 仅有列表端点，无处理接口 |
| `GET /api/v1/statistics/contracts` | ❌ 部分实现 | statistics 存在但数据硬编码 |
| `GET /api/v1/statistics/approval-efficiency` | ⚠️ 存在 | 但有硬编码数据 |
| `/api/v1/config/thresholds` | ❌ 未实现 | 审批规则配置 API |
| `GET /api/v1/ai-review/{review_id}/report` | ❌ 未实现 | 报告导出 |
| `WS /api/v1/ws/notifications` | ❌ 未实现 | WebSocket 实时通知 |
| `POST /api/v1/reminders/expiration` | ❌ 未实现 | 到期提醒配置 |

### 代码有、文档未提及的端点

| 端点 | 状态 | 说明 |
|------|------|------|
| `POST /api/v1/system/login` | ✅ 已实现 | 对接 user 表 + bcrypt 验证 + JWT 发放 |
| `GET /api/v1/system/users` | ✅ 已实现 | 分页 + 搜索 + 部门关联 |
| `GET /api/v1/system/roles` | ✅ 已实现 | 角色列表 |
| `GET /api/v1/system/departments` | ✅ 已实现 | 树形结构 |
| `GET /api/v1/system/profile` | ✅ 已实现 | 当前用户信息 |
| `GET /api/v1/ai-review/contracts/{id}/latest-review` | ✅ 已实现 | 最新审查结果（文档未提及） |
| `/health` | ✅ 已实现 | 健康检查 |

### 已对齐的端点

| 端点 | 对齐情况 |
|------|---------|
| `POST /api/v1/contracts` | ✅ 字段、响应格式对齐 |
| `GET /api/v1/contracts` | ✅ 分页 + 过滤参数对齐 |
| `GET /api/v1/contracts/{id}` | ✅ 对齐 |
| `PUT /api/v1/contracts/{id}` | ✅ 对齐 |
| `DELETE /api/v1/contracts/{id}` | ✅ 对齐（软删除） |
| `POST /api/v1/approvals/submit` | ✅ 对齐 |
| `POST /api/v1/approvals/{flow_id}/approve` | ✅ 对齐 |
| `GET /api/v1/approvals/pending` | ✅ 对齐 |
| `GET /api/v1/approvals/{flow_id}/history` | ✅ 对齐 |
| `POST /api/v1/ai-review/review` | ✅ 对齐（端点 `/review` 实际可用，但 api-spec 写的是 `/review`） |
| `GET /api/v1/ai-review/{review_id}/result` | ✅ 对齐 |

---

## 4. database-design.md — ORM 模型与设计对比

### 模型对齐表

| 表名 | DDL 文档 | ORM 代码 | 差异 |
|------|---------|---------|------|
| `contracts` | ✅ 有 `counterparty_id` | ❌ 缺少 `counterparty_id` 字段 | 🔴 设计有但代码无 |
| `contracts` | ✅ 有 `deleted_at` | ❌ 用 `status="deleted"` 软删除 | 🟡 实现方式不同 |
| `contracts` | `amount DECIMAL(15,2)` | `amount Float` | 🟡 精度不同 |
| `contract_versions` | ✅ 有 `UNIQUE KEY (contract_id, version)` | ❌ 无唯一约束 | 🟡 |
| `approval_flows` | ✅ 有 `idx_contract` | ❌ 无索引 | 🔴 文档有索引、代码未加 |
| `approval_steps` | ✅ 有 `idx_flow`、`idx_approver` | ❌ 无索引 | 🔴 |
| `ai_reviews` | ✅ 有 `idx_risk_score` | ❌ 无索引 | 🟡 |
| `risk_alerts` | ✅ 有 `idx_contract`、`idx_level` | ❌ 无索引（仅 ORM 定义） | 🟡 |
| `audit_logs` | ✅ 有 `idx_user`、`idx_action` | ❌ 无索引 | 🟡 |
| `counterparties` | ✅ DDL 完整 | ❌ **无任何 ORM 模型** | 🔴 设计有表、代码未建 |
| `seal_records` | DDL 有 `seal_id`, `user_id`, `approval_flow_id`, `watermark_hash`, `ip_address` | ORM 有 `contract_no`, `seal_method`, `operator`, `approver_id` | 🔴 字段差异大 |
| `contract_ledger` | ✅ 文档有 | ✅ 代码也有 | ✅ 一致 |
| `users` | ✅ DDL 完整 | ✅ ORM 完整，含 3 索引 | ✅ 一致 |
| `roles` | ✅ 6 个预置角色 | ✅ ORM 定义完整 | ✅ 一致 |
| `departments` | ✅ 完整 | ✅ 完整 | ✅ 一致 |

### 索引缺失总览（代码需补充）

| 表 | 文档有但代码无的索引 | 优先级 |
|----|---------------------|--------|
| `approval_flows` | `idx_contract (contract_id)`、`idx_status (status)` | P0（JOIN 必用） |
| `approval_steps` | `idx_flow (flow_id)`、`idx_approver (approver_id)`、`idx_status (status)` | P0 |
| `contract_versions` | `idx_hash (file_hash)`、`UNIQUE KEY (contract_id, version)` | P1 |
| `ai_reviews` | `idx_contract`、`idx_risk_level`、`idx_risk_score` | P1 |
| `risk_alerts` | `idx_contract`、`idx_type`、`idx_level`、`idx_status` | P1 |
| `audit_logs` | `idx_user`、`idx_action`、`idx_resource`、`idx_time` | P1 |

---

## 5. plan 文件状态汇总

### 各计划文件 vs 实际代码

| 计划文件 | 计划内容 | 实际状态 | 是否需关闭/更新 |
|---------|---------|---------|---------------|
| `design-freeze-improvement-plan.md` | 设计冻结 Phase A/B/C/D | **Phase A/B/D 已完成**，Phase C（四方签字）待办 | 🟡 更新 Phase C 状态 |
| `prototype-p0-p1-checklist.md` | 原型 P0/P1 修复 | **全部标记 ✅ 已完成** | ✅ 可归档 |
| `ai-review-sprint-plan.md` (Sprint 1) | 7 项 AI 前端改动 | **未执行**（前端 0 代码） | ❌ 仍有效 |
| `ai-review-sprint2-plan.md` | P1 前端体验增强 | **未执行** | ❌ 仍有效 |
| `review-implementation-plan.md` | 评审功能 Sprint 1/2 | **P0 端点已实现**，前端未动 | 🟡 部分完成 |

---

## 6. 代码实现度自评

### 后端 Sprint 完成度

| Sprint | 计划内容 | 完成度 | 详情 |
|--------|---------|--------|------|
| Sprint 0: 工程 + 认证 | 脚手架、JWT、配置、中间件 | **100%** | `main.py`(125行) + `config.py` + `security.py`(274行) + 3 middleware |
| Sprint 1: 合同 CRUD + 相对方 + MinIO | 合同 CRUD、相对方、文件上传 | **70%** | CRUD✅ 完整、相对方❌缺失、MinIO❌占位 |
| Sprint 2: 审批流引擎 | 三种流程 + 待办 | **95%** | 配置驱动✅ 完整、硬编码❌无 |
| Sprint 3: 评审工作台+退回 | 评审 + 退回修订 | **80%** | approve/reject/return 全✅ 需补 SLA |
| Sprint 4: AI 审查 | AI 引擎 + API | **85%** | 引擎 557 行✅ 完整、Celery mock❌未接 |
| Sprint 5: 用印 + 归档 + 消息 | 用印、归档、审计日志 | **80%** | seal✅ / archive✅ / audit✅ 部分逻辑 |
| Sprint 6: 看板 + 报表 | Dashboard + 统计 | **30%** | statistics 存在但硬编码 |

### 总体验收度

| 维度 | 文档要求 | 实际完成 | 达成率 |
|------|---------|---------|--------|
| 数据模型 | 13 张表 | 12 张（缺 Counterparty） | 92% |
| API 端点 | ~40 个（按 api-spec） | ~35 个已实现路由 | 88% |
| 鉴权 | JWT + 中间件 | ✅ 完整 | 100% |
| AI 核心 | TextExtractor → Engine → Scorer | 引擎✅ 557行 + Scorer + Parser + 种子 | 90% |
| 审批流 | 3 种流程 + approve/reject/return | ✅ 配置驱动 | 95% |
| 前端 Vue3 | 20 页面 Vue 组件 | 空目录 0 代码 | 0% |
| 数据库迁移 | Alembic | 无 migration 文件 | 0% |

---

## 7. 建议的文档更新清单

### P0 — 必须立即更新

1. **DESIGN_STATUS.md**：升级版本号，新增"代码实现状态"章节，移除"backend/ 不维护"声明
2. **development-kickoff.md**：改写为"开发进度"文件，标记 Sprint 0-5 已完成项
3. **database-design.md**：同步 `contracts` 缺少 `counterparty_id` 的差异，补充 `seal_records` 字段差异
4. **api-spec.md**：标记已实现端点状态，补充新增端点（`latest-review`, `/system/*`, `/health`）

### P1 — 应尽快更新

5. **README.md**：更新项目结构和技术栈说明
6. **ai-review-service.py vs Celery**：文档需注明 Celery task mock 状态
7. **DESIGN_STATUS §8 冻结状态**：更新为"设计已冻结 + 代码开发中"

### P2 — 可选优化

8. **plan 文件归档**：`prototype-p0-p1-checklist.md` 标记完成归档
9. **Sprint 计划**：合并过时计划，新建后端开发进度跟踪文件
