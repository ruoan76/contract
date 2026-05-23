# V1 开发启动清单

> 版本：1.0.0 | 日期：2026-05-18  
> 前置条件：[design-freeze-confirmation.md](./design-freeze-confirmation.md) 四方签字完成，DESIGN_STATUS ≥ 1.0.0。

---

## 1. 契约文档（实现必读）

| 优先级 | 文档 | 用途 |
|--------|------|------|
| P0 | [DESIGN_STATUS.md](./DESIGN_STATUS.md) | 范围、20 页（17 侧栏 + 3 下钻）、冻结决策 D8/D9 |
| P0 | [contract-status-dictionary.md](./contract-status-dictionary.md) | status / approval_status |
| P0 | [workflow-vs-review.md](./workflow-vs-review.md) | 双轨流程与节点 |
| P0 | [field-dictionary.md](./field-dictionary.md) | 表单 ↔ DB ↔ API |
| P0 | [api-page-mapping.md](./api-page-mapping.md) + [api-spec.md](./api-spec.md) | 接口与页面对齐 |
| P0 | [database-design.md](./database-design.md) | DDL、counterparties |
| P1 | [permission-matrix.md](./permission-matrix.md) | RBAC |
| P1 | [data-dictionary.md](./data-dictionary.md) | 枚举与分类 |
| 参考 | [ai-review-design.md](./ai-review-design.md) | AI 蓝图；V1 仅报告+置信度+反馈 |
| P1 | [contract-review-pro-seeds.md](../reference/contract-review-pro-seeds.md) + `backend/seeds/ai_review/generated/` | 规则/RAG 种子 JSON |

**原型**：`prototype/index.html` 为交互与文案基线，非生产代码。侧栏在原型中全展示；生产前端按 `permission-matrix` 隐藏菜单并实现 API 403。

---

## 2. 技术栈（已定稿）

MySQL 8 · Redis 7 · MinIO · FastAPI · Vue3 · Qwen（规划）

`backend/` 现有骨架**不沿用**；按 api-spec 重建或移除误导目录（见 DESIGN_STATUS §2）。

---

## 3. V1 明确不做

- 会签（PRD P2）  
- 审批委托生产逻辑（PRD P1，原型示意）  
- `page-risk` / `page-statistics` 独立页（D7）  
- 履约里程碑模块（PRD V2）  
- 移动端 H5（PRD 已修订）

---

## 4. 建议迭代顺序

```text
Sprint 0  工程脚手架 + 认证 + 合同 CRUD + 状态机
Sprint 1  起草/模板/相对方 + 文件存储(MinIO)
Sprint 2  审批流引擎(简易/标准/特殊) + 待办
Sprint 3  评审工作台(法务/财务/高管 Tab) + 退回修订
Sprint 4  AI 审查接口(Mock→Qwen) + 报告/反馈
Sprint 5  用印 + 归档 + 消息/审计
```

### 4.1 后端实现进度（2026-05-19）

| Sprint | 状态 | 交付 |
|--------|------|------|
| Sprint 0 | ✅ | approval_service 统一、Alembic、dev seed、User 依赖修复 |
| Sprint 1 | ✅ | Counterparty CRUD、黑名单、dashboard、upload、match-flow |
| Sprint 2 | ✅ | contract_state 状态机、approval_status 子状态、reject/return |
| Sprint 3 | ✅ | review_sessions/opinions、reviews API、修订提交 |
| Sprint 4 | ✅ | AI_REVIEW_MOCK 同步审查、feedback、用印列表、状态联动 |
| Sprint 5 | ✅ | config/thresholds、notifications、DEMO-01～05 集成测试 |

**测试**：`backend/tests/` **165/165** 通过；`integration/` **9/9**（IT-01～10）。

### 4.2 MySQL 本地迁移（Phase A）

```bash
# 1. 启动 MySQL（项目根目录）
docker compose up -d mysql

# 2. 迁移 + 种子
cd backend
export DATABASE_URL=mysql+asyncmy://contract_user:contract_password@localhost:3306/contract_db
alembic upgrade head
python scripts/seed_dev.py

# 3. 启动 API
uvicorn main:app --reload
```

### 4.3 后端完善进度（Phase A–D）

| Phase | 状态 | 说明 |
|-------|------|------|
| Phase A | ✅ | Alembic 002、待办过滤、多用户 fixture、IT-01~06 |
| Phase B | ✅ | 状态字典、评审门禁、看板、统计 |
| Phase C | ✅ | RBAC 最小集、删 workflow_service、技术债 |
| Phase D | ✅ | OpenAPI 导出、Postman 集合、联调清单 |

**OpenAPI 导出：**

```bash
cd backend && python scripts/export_openapi.py
# → backend/openapi.json
```

---

## 5. 验收对照

- [prd-v1-checklist.md](./prd-v1-checklist.md) P0 条目（实现后重新勾选）  
- [demo-script-v1.md](./demo-script-v1.md) 端到端场景  
- 状态迁移与 [contract-status-dictionary.md](./contract-status-dictionary.md) 一致

---

## 6. 变更管理

设计冻结后需求变更：更新 DESIGN_STATUS patch 版本 + PRD，并登记变更记录（CR 模板待补充）。
