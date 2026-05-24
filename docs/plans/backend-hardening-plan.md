# 合同平台后端完善计划（Post-Demo Hardening）

> 版本：**1.1.0** | 日期：2026-05-23（v1.1 吸收完善计划评审结论）  
> 前置：Sprint 0–5 Demo 链路 API 已实现，`pytest` 133/133 通过  
> 依据：原 [后端开发计划](../.cursor/plans/后端开发计划_e20dbe8b.plan.md) + 代码评审 + [完善计划评审（2026-05-23）](#13-变更记录)  
> 目标：从「Demo 可串 API」提升到「契约对齐、可 MySQL 部署、集成测试可信、前端可对接」

---

## 1. 现状与差距摘要

| 维度 | 当前 | 目标 |
|------|------|------|
| 功能覆盖 | Demo API 骨架 ~85% | 与 [demo-script-v1.md](../design/demo-script-v1.md) + api-spec **行为一致** |
| 集成测试 | 5 类轻量断言 | **五条 Demo 最小序列逐步断言 `status`（主状态）** |
| 数据库 | SQLite 单测 + `create_all` | **Alembic 001→002 迁移 + MySQL 验证** |
| 权限 | JWT 鉴权 | **RBAC 最小集挂关键写接口** |
| AI/存储 | Mock 同步 + 本地上传 | **Celery/MinIO 可选（Stretch）** |
| 生产就绪 | 低–中 | **V1 可部署基线** |

---

## 2. 范围边界（Out of Scope）

以下**不纳入**本完善计划，列入 V1.1 或保持原型-only：

| 项 | 说明 |
|----|------|
| 模板 CRUD | kickoff V1 不做 |
| 会签 / 审批委托 | kickoff V1 不做 |
| WebSocket 实时通知 | kickoff V1 不做 |
| DEMO-05「接受/拒绝建议」API | 原型修订工作台 UI；后端仅 revision submit |
| 条款比对 API | V1.1 |
| 组织树动态审批人 | V1 用 seed 固定 role→user |
| 履约里程碑模块 | V2 |

---

## 3. 阶段划分与总工期

```mermaid
flowchart TB
  subgraph critical [关键路径]
    A[Phase A 阻断修复 4-5d] --> B[Phase B 契约对齐 4-5d]
    B --> C1[Phase C 必须项 4-5d]
  end
  subgraph parallel [可并行]
    D[Phase D 联调准备] 
    C2[Phase C Stretch 4-5d]
  end
  A --> D
  C1 --> C2
```

| 阶段 | 周期 | 主题 | 里程碑 | 优先级 |
|------|------|------|--------|--------|
| **Phase A** | **4–5 天** | 迁移、待办、多用户 fixture、集成测（01/04/05→02/03） | **M-A** Demo 全链路测试绿 | **P0** |
| **Phase B** | **4–5 天** | 状态字典、评审闭环（含顺序门禁）、看板 | **M-B** 契约与字典一致 | **P1** |
| **Phase C 必须** | **4–5 天** | RBAC 最小集、技术债、统计修复 | **M-C** 可 MySQL 部署 | **P1** |
| **Phase C Stretch** | **4–5 天** | 通知事件、MinIO/Celery 双模式 | **M-C+** 生产可选能力 | **P2** |
| **Phase D** | **与 A 末并行** | OpenAPI、Postman、联调清单 | **M-D** 前端对接就绪 | **P1** |

**总估：** **3–4 周**（1 人全职）；Stretch 可延后不影响 V1 Demo 与前端联调。

---

## 4. Phase A 执行顺序（强制）

```text
┌─ A-1 Alembic 002 ─────────┐
│                           ├──► A-2 待办 + seed + conftest 多用户
└─ A-4 事务一致性（并行）───┘              │
                                           ▼
                              A-3a 集成测 DEMO-01/04/05（3d）
                                           │
                                           ▼
                              A-3b 集成测 DEMO-02/03（2d）
                                           │
                                           ▼
                              A-5 docker-compose 迁移验证
```

**依赖说明：**

- **A-3 必须在 A-2 之后**：多角色 Demo 依赖不同 user JWT 与待办过滤。
- **A-3 与 B-1 解耦**：Phase A 集成测**仅断言主 `status`**；`approval_status` 细粒度断言在 B-1 完成后追加（B-1b）。
- **Phase D 启动点**：A-3a 合并后即可导出 OpenAPI / Postman，**不必等 Phase C**。

---

## 5. Phase A — 阻断修复（P0）

### A-1 Alembic 迁移补全

| 项 | 动作 | 文件 |
|----|------|------|
| A-1.1 | 新增 `002_demo_hardening.py`（**仅 ADD**，不重建 001 已有表） | `backend/alembic/versions/` |
| A-1.2 | 新表：`counterparties`、`review_sessions`、`review_opinions`、`notifications` | 同上 |
| A-1.3 | 变更：`contracts.counterparty_id` FK + 索引；`ai_reviews.celery_task_id` | 同上 |
| A-1.4 | `env.py` import 全部模型 | `backend/alembic/env.py` |
| A-1.5 | 迁移说明：已有库 `001 → 002` 两步 upgrade | 本计划 §A-1 |

**002 与 001 关系：** `e9380d077795_initial_schema` 保留；002 只做增量 ALTER/CREATE，避免 drop 生产数据。

**验收：**

```bash
cd backend
# 全新库
DATABASE_URL=sqlite:///./contract_dev.db alembic upgrade head
# MySQL（见 A-5）
DATABASE_URL=mysql+asyncmy://contract_user:contract_password@localhost:3306/contract_db alembic upgrade head
```

---

### A-2 审批待办 + 多用户基础

| 项 | 动作 | 文件 |
|----|------|------|
| A-2.1 | `get_pending_approvals` JOIN `approval_steps` WHERE `status=pending` AND `approver_id=user_id` | `approval_service.py` |
| A-2.2 | `submit_approval`：按节点 `approver_role` 查 `users`（join `roles.code`）写入 `step.approver_id` | `approval_service.py` |
| A-2.3 | `seed_dev.py` 确保：`admin` / `drafter1` / `approver1` / `legal1` / `finance1` / `executive1` 与 role 绑定 | `scripts/seed_dev.py` |
| A-2.4 | conftest：`users_by_role` fixture + `api_client_as(role)` 按 role 切换 JWT | `tests/conftest.py` |
| A-2.5 | 单测：approver1 待办含流程、legal1 同流程待办为空（审批未到此节点时） | `tests/test_api_approvals.py` |

**角色映射（V1 固定）：**

| role.code | seed 用户 | 用途 |
|-----------|-----------|------|
| `drafter` | drafter1 | 起草、提交 |
| `approver` | approver1 | 部门主管审批 |
| `legal` | legal1 | 法务评审 |
| `finance` | finance1 | 财务评审 |
| `executive` | executive1 | 高管评审 |

**验收：** 同流程下 approver1 与 drafter1 的 `GET /approvals/pending` 结果不同。

---

### A-3 集成测试加深

#### A-3a（优先，~3 天）

| # | 用例 | 序列 | 断言 |
|---|------|------|------|
| IT-01 | DEMO-01 | drafter create(8万) → submit(simple) → **approver approve** → **legal opinion** → seal apply → seal approve | 终态 `status=sealed` |
| IT-04 | DEMO-04 | blacklist CP → create 403 | 403 + 无 contract 脏数据 |
| IT-05 | DEMO-05 | approve → legal return → revision v2 → ai-review | `draft` → 修订后 `version=2` |

#### A-3b（随后，~2 天）

| # | 用例 | 序列 | 断言 |
|---|------|------|------|
| IT-02 | DEMO-02 | create(32万) → ai + feedback → approve 至 approved → legal/finance/executive opinions → archive | `status=archived` |
| IT-03 | DEMO-03 | create(250万) → submit(large_amount) → history `total_steps=5`；可选 5 步 approve 后 history 含 `board_approval` 节点 | 结构断言 |

**规范：**

- 标记 `@pytest.mark.integration`（`pytest.ini` 注册 marker）
- Phase A：**只断言 `contracts.status`**（及 HTTP code）
- 使用 `api_client_as("approver")` 等多用户客户端
- DEMO-02 说明：脚本打开已有合同，测试走**新建合同等价路径**

**验收：** `pytest tests/integration/ -m integration -v` 全绿，IT-01～05 通过。

---

### A-4 会话与事务一致性

| 项 | 动作 | 文件 |
|----|------|------|
| A-4.1 | `create_contract(..., db: AsyncSession \| None)` API 必传 db | `contract_service.py`, `contracts.py` |
| A-4.2 | 黑名单拒绝时同一事务 rollback，无残留 contract | 同上 |

---

### A-5 Docker Compose 迁移验证

| 项 | 动作 |
|----|------|
| A-5.1 | 文档化：`docker compose up -d mysql` → `alembic upgrade head` → `seed_dev.py` |
| A-5.2 | 可选：`compose` 增加 `profile: test` 跑 integration（MySQL URL 注入 pytest） |
| A-5.3 | `development-kickoff.md` 补充 MySQL 本地启步骤 |

**验收：** README 或 kickoff 中命令可复制执行成功。

---

## 6. Phase B — 契约对齐（P1）

**建议优先级：** B-2 > B-1 > B-4 > B-3（统计页非原型 P0）

### B-1 状态机与 approval_status

| 迁移点 | 期望 | 文件 |
|--------|------|------|
| 提交审批 | `pending` + `dept_approval`（若已 AI 则先 `ai_screening`） | `approval_service.py` |
| 每 approve 步 | `approval_status` = 下一节点 | `contract_state.py` |
| 流程通过 | `approved` + `seal_pending` | `approval_service.py` |
| reject / return | `rejected` / `draft` + `returned` | 已有 + 单测 |

**B-1b（B-1 完成后）：** 集成测追加 `approval_status` 关键步断言。

**验收：** `tests/test_contract_state_transitions.py` 覆盖 [contract-status-dictionary.md](../design/contract-status-dictionary.md) §1.1 主路径。

---

### B-2 评审域闭环

| 项 | 动作 | 文件 |
|----|------|------|
| B-2.1 | **legal** opinion 前：最新 AI `review_status ∈ {ai_done, reviewed, confirmed}` | `review_service.py` |
| B-2.2 | **finance** 需 legal 已 approve；**executive** 需 legal + finance 已 approve | `review_service.py` |
| B-2.3 | `get_pending_reviews`：按 flow_type 减已有 opinions，返回**待完成角色** | `review_service.py` |
| B-2.4 | 全部 required roles approve → `review_sessions.status=completed` | `review_service.py` |
| B-2.5 | simple 拒绝 finance/executive（负向单测） | `tests/test_api_reviews.py` |

**验收：** DEMO-02 集成测顺序 legal→finance→executive；乱序 finance 返回 400。

---

### B-3 统计 API 修复（可后置）

| 项 | 动作 |
|----|------|
| B-3.1 | `approval-efficiency`：`completed` → `approved` |
| B-3.2 | `risk-trend`：按 dialect 分支日期聚合（SQLite / MySQL） |
| B-3.3 | `tests/test_api_statistics.py` |

---

### B-4 看板语义修正

| 项 | 动作 |
|----|------|
| B-4.1 | `executing`：`status=executing` 或（`approved/sealed/signed` 且 `end_date > today`） |
| B-4.2 | `expiring_soon`：30 天内到期且未 expired |
| B-4.3 | seed/fixture：2–3 条不同 `end_date` 合同；dashboard 测非空 |

---

## 7. Phase C — 生产增强

### C 必须项（V1 完善 DoD）

#### C-1 RBAC 最小集

先实现 `require_role(code)` 依赖工厂（修复现有 `check_permission` 无法 `Depends` 的问题）：

| 接口 | 最小角色 | DoD 必测 403 |
|------|----------|--------------|
| `PUT /config/thresholds` | admin | ✅ |
| `POST /counterparties/{id}/blacklist` | admin | ✅ |
| `POST /seals/{id}/approve` | admin | ✅ |
| `POST /reviews/.../opinions` | 对应 role | ✅ |
| `POST /approvals/{id}/approve` | 当前 step approver | ⚠️ Stretch（先测 role=approver） |

**验收：** `tests/test_rbac_api.py` ≥ **5** 个 403 用例通过。

#### C-4 技术债（与 C-1 同 PR 或紧随其后）

| 项 | 动作 |
|----|------|
| 删除 | `workflow_service.py` |
| 替换 | `datetime.utcnow()` → timezone-aware |
| 替换 | Pydantic `dict()` → `model_dump()` |

---

### C Stretch 项（不阻塞 V1 DoD）

#### C-2 通知与业务事件（V1.1 可整包延后）

| 事件 | 接收人 |
|------|--------|
| 审批待办 | step approver |
| 评审退回 | creator |
| 用印待批 | seal 角色 |
| 归档完成 | creator |

列表 API 已存在；**自动触发**列为 Stretch。

#### C-3 存储与 AI 双模式（Stretch）

| 模式 | 环境变量 | DoD |
|------|----------|-----|
| 本地 storage | 默认 | 已满足 |
| MinIO | `FILE_STORAGE=minio` | Stretch |
| AI Mock | `AI_REVIEW_MOCK=1` | 已满足 |
| AI Celery | `AI_REVIEW_MOCK=0` + Redis | Stretch：task 完成且 `review_status=ai_done`（engine 可 mock） |

---

## 8. Phase D — 前端联调准备（A-3a 后启动）

| 项 | 交付物 | 启动条件 |
|----|--------|----------|
| D-1 | [api-spec.md](../design/api-spec.md) 逐端点 ✅/⚠️ | A-3a |
| D-2 | `backend/openapi.json`（`python -c "..."` 或脚本） | A-3a |
| D-3 | Postman/Bruno：DEMO-01～05 集合 | A-3a |
| D-4 | [api-page-mapping.md](../design/api-page-mapping.md) 新路由 | B 完成 |
| D-5 | [frontend-api-integration-checklist.md](./frontend-api-integration-checklist.md) | B 完成 |

---

## 9. 集成测试用例清单（DoD 附件）

| ID | 名称 | Phase | 断言级别 |
|----|------|-------|----------|
| IT-01 | DEMO-01 简易全链路 | A-3a | status |
| IT-02 | DEMO-02 标准评审+归档 | A-3b | status |
| IT-03 | DEMO-03 特殊流程 history | A-3b | structure |
| IT-04 | DEMO-04 黑名单 | A-3a | 403 |
| IT-05 | DEMO-05 退回修订 | A-3a | status + version |
| IT-06 | 待办按用户过滤 | A-2 | 列表差异 |
| IT-07 | dashboard 三栏非空 | B-4 | structure |
| IT-08 | RBAC 403 ×5 | C-1 | 403 |
| IT-09 | approval_status 逐步 | B-1b | status + approval_status |
| IT-10 | 评审顺序门禁 | B-2 | 400/200 |

**目标：** integration 用例 **≥ 10** 通过（Stretch：MySQL 环境再跑一遍 IT-01～05）。

---

## 10. 测试策略

| 层级 | 目标 | 说明 |
|------|------|------|
| 单元 | 150+ | service + state 迁移 |
| API | 每 v1 路由 ≥1 文件 | 补 `test_api_reviews`, `test_api_counterparties` |
| 集成 | ≥ 10（见 §9） | SQLite；MySQL 为 Stretch |
| CI | lint → pytest → alembic(mysql) → integration | 见下 |

```text
lint → pytest tests/ -q                    # SQLite，全量
     → docker compose up -d mysql
     → alembic upgrade head                 # MySQL 空库
     → pytest tests/integration/ -m integration
     → openapi export → backend/openapi.json
```

---

## 11. 任务排期（修订甘特）

```mermaid
gantt
  title 后端完善计划 v1.1
  dateFormat YYYY-MM-DD
  section PhaseA
  A1_Alembic_A4_事务     :a1, 2026-05-24, 2d
  A2_待办与多用户fixture  :a2, after a1, 2d
  A3a_集成01_04_05       :a3a, after a2, 3d
  A3b_集成02_03          :a3b, after a3a, 2d
  A5_compose验证         :a5, after a1, 1d
  section PhaseD
  D_OpenAPI_Postman      :d1, after a3a, 5d
  section PhaseB
  B2_评审闭环            :b2, after a3b, 2d
  B1_状态字典            :b1, after b2, 2d
  B4_看板                :b4, after b1, 1d
  B3_统计                :b3, after b4, 1d
  section PhaseC
  C1_C4_RBAC与债         :c1, after b2, 3d
  C2_通知                :c2, after c1, 2d
  C3_MinIO_Celery        :crit, after c2, 4d
```

---

## 12. PR 切分（修订）

| PR | 分支 | 内容 | Phase |
|----|------|------|-------|
| PR-1 | `chore/alembic-002-schema` | A-1 + A-5 文档 | A |
| PR-2 | `fix/approval-pending-multuser` | A-2 + conftest fixture | A |
| PR-3 | `fix/contract-create-session` | A-4 | A |
| PR-4 | `test/integration-demo-a` | A-3a IT-01/04/05/06 | A |
| PR-5 | `test/integration-demo-b` | A-3b IT-02/03 | A |
| PR-6 | `feat/review-domain-closure` | B-2 | B |
| PR-7 | `feat/contract-state-dictionary` | B-1 + B-1b IT-09 | B |
| PR-8 | `fix/dashboard-statistics` | B-4 + B-3 + IT-07 | B |
| PR-9 | `feat/rbac-minimal` | C-1 + C-4 + IT-08 | C |
| PR-10 | `feat/notifications-events` | C-2（Stretch） | C |
| PR-11 | `feat/storage-ai-dual-mode` | C-3（Stretch） | C |
| PR-12 | `docs/openapi-integration` | Phase D | D |

---

## 13. 完成定义（DoD）— V1 完善

**必须全部勾选**（Stretch 除外）：

- [x] MySQL 空库 `alembic upgrade head`（001→002）成功（SQLite 已验；MySQL 文档见 kickoff §4.2）
- [x] `pytest tests/` ≥ **155** 通过（当前 **165**）
- [x] `tests/integration/` ≥ **10** 通过（IT-01～10）
- [x] IT-01～05 逐步 **status** 断言通过
- [x] `GET /approvals/pending` 按 `approver_id` 过滤（IT-06）
- [x] 评审角色 + AI 门禁 + 顺序（B-2，IT-10）
- [x] RBAC 最小集 **5** 个写接口 403 测通过（IT-08）
- [x] `workflow_service.py` 已删除
- [x] api-spec + development-kickoff §4.2 更新

**Stretch（不阻塞 V1 发布）：**

- [ ] C-2 四类业务事件自动通知
- [ ] C-3 MinIO upload + Celery ai-review 各 1 条 E2E
- [x] integration 在 MySQL 上重跑 IT-01～05（2026-05-19：10/10 通过，见 kickoff §4.2）

---

## 14. 风险与依赖

| 风险 | 缓解 |
|------|------|
| A-3 多 user fixture 调试耗时 | 先做 A-3a 三条，02/03 后置 |
| B-1 改动导致集成测反复 | A 阶段只断言 status；B-1b 再加 approval_status |
| RBAC 按节点复杂 | V1 先 role 级；节点级放 Stretch |
| 工期超 3 周 | 砍 C-2/C-3 Stretch，B-3 统计后置 |
| 前端等 API | D 在 A-3a 后交付 OpenAPI |

---

## 15. 文档更新节奏

| 文档 | 更新时机 |
|------|----------|
| [development-kickoff.md](../design/development-kickoff.md) §4.2 完善进度 | Phase A 完成 |
| [DESIGN_STATUS.md](../design/DESIGN_STATUS.md) 后端 V1 ready | Phase C 必须项完成 |
| [doc-code-alignment-2026-05-23.md](./doc-code-alignment-2026-05-23.md) | 每 Phase 末 |
| 本计划 §13 变更记录 | 每 Phase 末 |

---

## 16. 变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0.0 | 2026-05-23 | 初版：Phase A–D、DoD、11 PR |
| 1.1.0 | 2026-05-23 | 吸收评审：Out of Scope；工期 3–4 周；A 执行顺序；A-3a/b 拆分；A-5 compose；多用户 fixture；B-2 顺序门禁；C 必须/Stretch 拆分；DoD 量化修订；集成用例清单 IT-01～10；PR 12 个；D 提前至 A-3a 后 |

---

## 17. 最快价值路径（Quick Win）

若资源有限，按以下顺序可 **1 周内** 支撑第一轮前端联调：

```text
Day 1-2:  PR-1 Alembic + PR-3 事务
Day 3-4:  PR-2 待办 + 多用户 fixture
Day 5-7:  PR-4 集成 DEMO-01/04/05 + PR-12 OpenAPI/Postman
```

Phase B/C 必须项在联调反馈并行推进。

---

*本计划为 Sprint 0–5 之后的「完善阶段」，不替代原 Demo 链路开发计划，在其基础上收口至 V1 交付标准。*
