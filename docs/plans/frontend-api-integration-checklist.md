# 前端 API 联调清单（草案）

> 版本：**0.6.0** | 日期：2026-05-19  
> 前置：[backend-hardening-plan.md](./backend-hardening-plan.md) Phase D  
> 用途：20 页原型 ↔ 后端 API 对照，联调时逐项勾选  
> OpenAPI：`backend/openapi.json`（`python backend/scripts/export_openapi.py`）  
> Postman：`backend/postman/demo-01-05.json`

---

## 使用说明

- **P0**：Demo 脚本必须可用  
- **P1**：页面主流程可用  
- **P2**：增强/筛选/统计  
- 状态：`⬜ 未测` `🟡 部分` `✅ 通过`  
- **后端 IT**：集成测 IT-01~10（pytest `-m integration`）  
- **Vue3 浏览器**：`frontend/` + `npm run dev`（:8080，需 backend :8000）

---

## 实机联调记录（2026-05-19）

| 项 | 方式 | 结果 |
|----|------|------|
| DEMO-01~05 全链路 | `node prototype/_api-demo-test.mjs` | ✅ API 契约 ✅ |
| Vue3 Phase 3 | review-history + 列表筛选 + executive + E2E CI | ✅ Phase 3 ✅ |
| Vue3 Phase 2 | messages/config/audit/users + D10 详情 + Playwright | ✅ Phase 2 ✅ |
| 原型 Mock 回归 | `node prototype/_run-tests.mjs` | ✅ 147/147（原型冻结） |
| API 层 | `frontend/src/api/` 自 prototype 迁移 | ✅ |


## 侧栏页面映射

| 原型 page | 页面名 | 主要 API | 优先级 | 状态 |
|-----------|--------|----------|--------|------|
| dashboard | 合同看板 | `GET /contracts/dashboard` | P0 | ✅ |
| create | 新建合同 | `GET /counterparties`, `POST /contracts`, `GET /contracts/match-flow` | P0 | ✅ |
| contracts | 合同列表 | `GET /contracts`（分页/筛选） | P0 | ✅ |
| contract-detail | 合同详情 | `GET /contracts/{id}` | P0 | ✅ |
| approvals | 待办审批 | `GET /approvals/pending`, `POST /approvals/{id}/approve` | P0 | ✅ |
| review-center | 评审中心 | `GET /reviews/pending` | P1 | ✅ |
| review-workspace | 评审工作台 | `GET /reviews/contracts/{id}`, `POST .../opinions`, `POST .../return` | P0 | ✅ |
| review-history | 评审历史 | `GET /reviews/contracts/{id}/history` | P1 | ✅ |
| approval-history | 审批历史（下钻） | `GET /approvals/{flow_id}/history` | P1 | ✅ |
| revision-workspace | 修订工作台 | `POST /contracts/{id}/revisions` | P0 | ✅ |
| ai-review | 审查报告 | `POST /ai-review/review`, `GET .../latest-review`, `POST .../feedback` | P0 | ✅ |
| seal | 用印管理 | `GET /seals`, `POST /seals/apply`, `POST /seals/{id}/approve` | P0 | ✅ |
| archives | 归档台账 | `GET /archives`, `POST /archives`（以实际路由为准） | P1 | ✅ |
| counterparties | 相对方 | `GET/POST/PUT /counterparties`, `POST .../blacklist` | P0 | ✅ |
| config | 审批配置 | `GET/PUT /config/thresholds` | P1 | ✅ |
| messages | 消息中心 | `GET /notifications`, `PATCH /notifications/{id}/read` | P2 | ✅ |
| audit | 审计日志 | `GET /audit` | P2 | ✅ |

---

## Demo 脚本联调序列

| Demo | 步骤 | API 链 | 状态 |
|------|------|--------|------|
| DEMO-01 | 1–5 | create → submit → approve → review → seal | ✅ Vue3 ✅ |
| DEMO-02 | 1–4 | ai-review → opinions×3 → archive | ✅ Vue3 ✅ |
| DEMO-03 | 1–2 | thresholds → approval history | ✅ Vue3 ✅ |
| DEMO-04 | 1–2 | counterparties blacklist → create 拒绝 | ✅ Vue3 ✅ |
| DEMO-05 | 1–2 | review return → revision → ai-review | ✅ Vue3 ✅ |

---

## 多角色 JWT 切换

联调时需验证的角色（对应 seed_dev）：

| 角色 | 用户 | 典型页面 |
|------|------|----------|
| 业务员 | drafter1 | create, contracts |
| 部门主管 | approver1 | approvals |
| 法务 | legal1 | review-workspace |
| 财务 | finance1 | review-workspace |
| 高管 | executive1 | review-workspace |
| 管理员 | admin | config, blacklist |

---

*Phase B 完成后与本清单同步更新 api-page-mapping.md。*
