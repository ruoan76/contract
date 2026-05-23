# 合同审批管理平台 — 架构设计

> 版本：V1.0 | 日期：2026-05-23  
> 状态：**已实现（后端 60%）** · 设计冻结 v0.5.3 详见 [DESIGN_STATUS.md](./design/DESIGN_STATUS.md)

本文档收敛项目架构设计与技术选型的完整决策过程，作为系统架构的单一真相源。

---

## 一、系统目标

### 1.1 业务目标

合同审批管理平台，覆盖合同全生命周期：**起草 → AI 审查 → 多级审批 → 用印 → 归档 → 台账**。
核心差异化能力：**AI 智能合同审查**（基于本地 LLM + 规则引擎 + RAG 法规库）。

### 1.2 非功能性约束

| 约束 | 说明 |
|------|------|
| **数据不出本地** | 合同涉及商业机密，AI 模型和所有数据必须本地部署 |
| **团队规模** | 1–2 名全栈开发（MVP 阶段），技术栈必须轻量 |
| **开发周期** | V1 MVP 8 周上线，快速迭代 |
| **硬件环境** | 开发机：Apple Silicon Mac（M 系列）；生产：待定 |

---

## 二、总体架构

### 2.1 分层架构（已实现）

```
┌─────────────────────────────────────────────────────────────────┐
│  前端层 (Vue3 + TypeScript)                                      │
│  20 页面：看板/消息/起草/列表/模板/AI审查/评审/审批/用印/归档/…    │
│  当前状态：工程脚手架已创建，待开发（原型以 HTML/JS 高保真运行）     │
└─────────────────────────────────────────────────────────────────┘
                              │ HTTP/REST
┌─────────────────────────────────────────────────────────────────┐
│  API 网关 (Nginx) + CORS + 反向代理                                │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│  后端服务层 (FastAPI + Async SQLAlchemy)                          │
│  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │合同 CRUD   │ │审批引擎  │ │AI审查    │ │风险预警  │          │
│  │531 行服务  │ │496 行    │ │557 行引擎│ │服务就绪  │          │
│  └───────────┘ └──────────┘ └──────────┘ └──────────┘          │
│  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │用印管理   │ │归档服务  │ │审计日志  │ │系统管理  │          │
│  │195 行     │ │服务就绪  │ │服务就绪  │ │164 行 API│          │
│  └───────────┘ └──────────┘ └──────────┘ └──────────┘          │
│  中间件：Auth (JWT) + Audit + Logging                             │
└─────────────────────────────────────────────────────────────────┘
                              │
┌────────────────────┬──────────────────┬──────────────────────┐
│  MySQL 8           │  Redis 7         │  MinIO               │
│  12 核心表          │  Cache + Queue   │  合同文件存储          │
│  +索引策略         │  Broker           │  S3 兼容 API          │
└────────────────────┴──────────────────┴──────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│  Celery Worker (异步任务)                                         │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐ │
│  │ ai_review.contract_review │  │ notification_tasks           │ │
│  │ 重试 3 次 · 60s 延迟       │  │ 邮件/企微通知（规划）           │ │
│  └──────────────────────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│  AI 引擎 (Qwen3.6 35B-A3B-4bit via OpenAI SDK)                    │
│  Apple Silicon MLX 本地部署                                       │
│  五维并行审查：合规 30% + 风险 25% + 财务 20% + 履约 15% + 异常 10%  │
│  Pydantic 结构化输出 · JSON schema 约束                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 服务调用关系

```
创建合同 ──▶ 提交审批 ──▶ AI 初筛(Celery) ──▶ 法务评审 ──▶ 财务评审
                │                              │
          ApprovalFlow                    review-workspace
                │                              │
          approve_step()                  ApprovalStep 记录
                                                │
                                           用印申请 ──▶ 归档 ──▶ 台账
```

### 2.3 目录结构

```
contract/
├── backend/
│   ├── main.py                    # FastAPI 入口 (125 行)
│   ├── app/
│   │   ├── api/v1/                # 11 个路由模块
│   │   │   ├── contracts.py       # 合同 CRUD (114 行)
│   │   │   ├── approvals.py       # 审批流程 (99 行)
│   │   │   ├── ai_review.py       # AI 审查 (151 行)
│   │   │   ├── system.py          # 登录/用户/角色/部门 (164 行)
│   │   │   ├── risks.py / seals.py / archives.py / audit.py / statistics.py
│   │   ├── core/
│   │   │   ├── config.py          # Pydantic Settings (79 行)
│   │   │   ├── security.py        # JWT + bcrypt + 权限依赖 (274 行)
│   │   ├── db/
│   │   │   ├── database.py        # Async Session 配置
│   │   │   └── base.py            # SQLAlchemy Base
│   │   ├── models/                # 9 个唯一 SQLAlchemy 模型（3 文件；contract.py 中 3 个重复定义已被 ai_review.py 覆盖）
│   │   │   ├── contract.py        # Contract/Version/Flow/Step/SealRecord/Ledger (321 行)
│   │   │   ├── user.py            # User/Role/Department（⚠️ 缺 `from sqlalchemy.orm import relationship`）
│   │   │   └── ai_review.py       # AIReview/RiskAlert/AuditLog
│   │   ├── services/              # 业务逻辑
│   │   │   ├── contract_service.py    # 合同 CRUD (531 行)
│   │   │   ├── approval_service.py    # 审批引擎 (496 行)
│   │   │   ├── ai_review_service.py   # 审查协调 (286 行)
│   │   │   ├── seal_service.py        # 用印 (195 行)
│   │   │   ├── ai_review/
│   │   │   │   ├── ai_engine.py       # AI 审查引擎 (557 行) ⭐
│   │   │   │   ├── clause_parser.py   # 条款解析
│   │   │   │   ├── risk_scorer.py     # 风险评分
│   │   │   │   ├── text_extractor.py  # 文本提取
│   │   │   │   └── seed_store.py      # 种子数据
│   │   │   ├── audit/ / risk/ / document/ (子目录)
│   │   ├── middleware/
│   │   │   ├── auth_middleware.py     # JWT Bearer (129 行)
│   │   │   ├── audit_middleware.py    # 操作审计
│   │   │   └── logging_middleware.py  # 请求日志
│   │   ├── celery_tasks/            # Celery 异步任务
│   │   │   ├── ai_review_tasks.py   # 审查任务 (160 行)
│   │   │   └── notification_tasks.py
│   │   └── schemas/                 # Pydantic DTO
│   ├── alembic/                     # 数据库迁移（versions 待生成）
│   ├── seeds/ai_review/             # AI 种子数据导入
│   └── requirements.txt             # 39 个依赖
├── frontend/src/                    # Vue3 工程（脚手架已创建，待开发）
├── prototype/                       # HTML/JS 高保真原型（20 页，可运行）
├── docs/
│   ├── design/                      # 正式设计文档
│   ├── reference/                   # 专题设计参考
│   ├── plans/                       # Sprint 实施计划
│   └── archive/                     # 历史审计（Superseded）
├── docker-compose.yml               # 开发环境一键启动
└── nginx.conf                       # 反向代理
```

---

## 三、技术选型

### 3.1 后端框架：FastAPI

| 对比项 | FastAPI ✅ | Django REST | Flask |
|--------|-----------|-------------|-------|
| 异步原生 | ✅ async/await 全链路 | ❌ 仅 4.2 起支持 | ❌ 需额外扩展 |
| 性能 | ~100K req/s (uvicorn) | ~10K req/s | ~20K req/s |
| 自动文档 | ✅ OpenAPI + Swagger UI | ❌ 需 drf-spectacular | ❌ 需 flask-openapi |
| 类型安全 | ✅ Pydantic 强校验 | ⚠️ Serilizer 弱类型 | ❌ 无内置校验 |
| AI 集成 | ✅ AsyncOpenAI 无缝对接 | ⚠️ 需自定义 | ⚠️ 需自定义 |
| 学习曲线 | 低（Pythonic） | 高（约定多） | 低 |
| 开发速度 | 快（代码即文档） | 慢（大量约定） | 中等 |

**决策理由**：
1. **FastAPI 的 async 原生支持**是核心理由。AI 审查需并行 5 维 LLM 调用（`asyncio.gather`），同步框架无法优雅实现
2. **Pydantic 强类型**让 request/response 自文档化，与 TypeScript 前端对接无歧义
3. 团队成员熟悉，上手成本 0
4. OpenAPI 自动生成 — 前端可直接用 openapi-generator 生成 SDK

### 3.2 数据库：MySQL 8（非 PostgreSQL）

| 对比项 | MySQL 8 ✅ | PostgreSQL |
|--------|-----------|------------|
| JSON 字段 | ✅ 支持 `JSON` 类型（AI 审查结果、审计日志） | ✅ JSONB 更强 |
| 异步驱动 | ✅ `asyncmy`（纯 Python，性能好） | ⚠️ `asyncpg` 需编译安装 |
| 团队经验 | ✅ 企业主力数据库，全员有经验 | ⚠️ 部分成员不熟悉 |
| Apple Silicon 兼容 | ✅ Docker 原生运行 | ✅ Docker 原生运行 |
| 全文索引 | ✅ 5.7+ 支持 | ✅ 更成熟 |

**决策理由**：
1. 初始选型考虑 PostgreSQL（JSONB 更适合存储 review 结果），但 `asyncpg` 在 Apple Silicon 上编译安装不顺畅，`asyncmy` 零配置
2. MySQL 8 的 JSON 类型已完全满足 AI 审查结果（clause_reviews JSON）、审计日志（detail JSON）的场景
3. 公司现有运维体系以 MySQL 为主，生产部署无需引入新组件

### 3.3 前端框架：Vue3 + TypeScript

| 对比项 | Vue3 ✅ | React |
|--------|---------|-------|
| 学习曲线 | 低（模板直观） | 中（JSX hook 模式） |
| 生态 | Vue Router + Pinia 成熟 | Next.js / Remix 生态更大 |
| TypeScript | ✅ 3.x 完全支持 | ✅ 原生支持 |
| 团队经验 | ✅ 主力 Vue2，升级 Vue3 顺畅 | ❌ 无使用经验 |
| 组件库 | Element Plus（企业后台首选） | Ant Design |

**决策理由**：
1. 团队长期用 Vue2，升级到 Vue3 学习成本最小
2. Element Plus 是成熟的企业级后台 UI 库，覆盖表格、表单、对话框等管理后台必备组件，零定制成本
3. 高保真原型已定义交互模式，Vue3 迁移只需转模板 + 接入 API

### 3.4 AI 引擎：Qwen3.6 35B-A3B-4bit

| 对比项 | Qwen3.6 ✅ | GPT-4o API | DeepSeek |
|--------|-----------|------------|----------|
| 部署方式 | ✅ 本地运行（MLX on Apple Silicon） | ❌ 云端 API | ✅ 可本地 |
| 数据隐私 | ✅ 合同内容不出本机 | ❌ 传到云端 | ✅ 可本地 |
| 中文合同理解 | ✅ 通义系列在中文法律场景表现优秀 | ✅ 优秀 | ✅ 优秀 |
| 推理速度 | ~3 tokens/s（35B-4bit on M2 Max） | 快 | ~3 tokens/s |
| 成本 | ✅ 零 API 费用 | ❌ 按 token 计费 | 免费/可本地 |
| 4-bit 量化 | ✅ MLX 原生支持 4-bit | N/A | ✅ GGUF |

**决策理由**：
1. **数据隐私是第一原则**，合同内容必须不出公司环境
2. Qwen 系列在中文法律/商业合同场景的理解能力优于同级别开源模型
3. MLX 框架为 Apple Silicon 原生优化，35B-A3B-4bit 在 M2 Max 上推理可接受
4. 4-bit 量化将模型内存控制在 ~20GB，消费级 Apple Silicon 可用
5. 兼容 OpenAI SDK 接口（通过 `openai-python` 库直连本地 endpoint），代码零定制

### 3.5 任务队列：Celery + Redis

| 对比项 | Celery ✅ | ARQ | Dramatiq |
|--------|-----------|-----|----------|
| AI 审查集成 | ✅ 成熟生态，重试/监控完善 | ⚠️ 生态小 | ✅ 简洁 |
| 可视化监控 | ✅ Flower 开箱即用 | ❌ 无 | ⚠️ 有限 |
| 团队经验 | ✅ 标准 Python 任务队列 | ❌ 不熟 | ❌ 不熟 |
| Redis 集成 | ✅ 原生 | ✅ 原生 | ✅ 原生 |

**决策理由**：
1. AI 审查是重计算（5 维 LLM 并行，单合同 2–5 分钟），必须异步执行
2. Celery 的 retry 机制（max_retries=3, default_retry_delay=60）已内置到 `ai_review_tasks.py`
3. Redis 既是 Cache 又是 Broker，架构极简（无需 RabbitMQ）

### 3.6 对象存储：MinIO（200 行全实现）

（`MinIOStorage` wrapper 已在 `storage.py` 完整实现：`upload_file`/`download_file`/`presigned_url`/`delete_file`，通过 `loop.run_in_executor` 转异步。仅在 `contract_service.py` 内调用被注释为 `# await storage.upload_file(...)`，需取消注释启用。）

| 对比项 | MinIO ✅ | 本地文件系统 | AWS S3 |
|--------|----------|-------------|--------|
| S3 兼容 | ✅ 完全 | ❌ | ✅ |
| 本地部署 | ✅ Docker 一行启动 | ✅ | ❌ |
| 权限控制 | ✅ 桶级 + 对象级 | ⚠️ POSIX 权限 | ✅ |
| 迁移成本 | 低（S3 协议通用） | 高（迁移 S3 需重写） | 0 |

**决策理由**：
1. 合同文件（PDF/Word/图片）需持久存储，MinIO Docker 一行即可本地运行
2. S3 兼容 API 确保未来迁移云存储不改代码（换 endpoint + credentials 即可）
3. MinIO 内置 Web 控制台，开发调试方便

### 3.7 ORM：SQLAlchemy 2.0（Async）

| 对比项 | SQLAlchemy 2.0 Async ✅ | Tortoise ORM | Prisma Python |
|--------|-------------------------|-------------|---------------|
| Async 支持 | ✅ 成熟（2.0 正式支持） | ✅ 原生 Async | ✅ 原生 Async |
| 类型安全 | ✅ mypy 友好 | ⚠️ 有限 | ✅ 代码生成 |
| 团队经验 | ✅ 熟悉 | ❌ 不熟 | ❌ 不熟 |
| 生态 | 最大 Python ORM | 较小 | 小 |
| Alembic 迁移 | ✅ 标配 | ❌ 自建 | 自建 |

**决策理由**：
1. 团队熟悉 SQLAlchemy，上手即写
2. SQLAlchemy 2.0 的 `Mapped[]` 类型注解 + mypy 校验保障 ORM 模型安全
3. Alembic 是 Python 生态最成熟的 migrator（当前 versions 待生成，下一步补）

### 3.8 技术栈汇总表

| 层级 | 技术 | 版本 | 用途 | 状态 |
|------|------|------|------|------|
| **前端** | Vue3 | 3.x | SPA 框架 | 🏗️ 目录已创建，待开发 |
| **前端** | TypeScript | 5.x | 类型 | 🏗️ |
| **前端** | Element Plus | 2.x | UI 组件库 | 🏗️ |
| **前端原型** | HTML/JS | — | 高保真原型（20 页） | ✅ 可运行 |
| **网关** | Nginx | alpine | 反向代理 / CORS | ✅ |
| **后端** | FastAPI | 0.109.0 | REST API 框架 | ✅ 实现中 |
| **后端** | SQLAlchemy | 2.0.25 | 异步 ORM | ✅ |
| **后端** | Pydantic | 2.5.3 | 数据校验 | ✅ |
| **后端** | Celery | 5.3.6 | 异步任务 | ✅ |
| **数据库** | MySQL | 8.0 | 关系数据 | 📦 Docker ready |
| **缓存/队列** | Redis | 7-alpine | Cache + Broker | 📦 |
| **存储** | MinIO | latest | 文件存储 | 📦 |
| **AI 模型** | Qwen3.6 35B-A3B-4bit | MLX | 合同审查 | ✅ 引擎已实现 |
| **AI SDK** | openai | 1.12.0 | 统一 AI 接口 | ✅ |
| **AI 引擎** | MLX | 0.31.2 | Apple Silicon 推理 | ✅ |
| **文档处理** | PyMuPDF | 1.23.8 | PDF 文本提取 | ✅ |
| **文档处理** | python-docx | 1.1.0 | Word 解析 | ✅ |
| **文档处理** | EasyOCR | 1.7.1 | OCR（扫描件） | ✅ |
| **认证** | python-jose | 3.3.0 | JWT 签发/验证 | ✅ |
| **认证** | passlib[bcrypt] | 1.7.4 | 密码哈希 | ✅ |
| **部署** | Docker Compose | 3.8 | 开发环境编排 | ✅ |
| **迁移** | Alembic | 1.13.1 | DB 迁移 | 📦 待生成首版 |
| **测试** | pytest | 7.4.4 | 单元测试 | 🏗️ |

---

## 四、关键架构决策

### 4.1 决策记录（ADR）

| ID | 决策 | 背景 | 备选 | 理由 | 代码验证 |
|----|------|------|------|------|----------|
| **ADR-01** | AI 本地部署，不上云 | 合同涉及商业机密 | GPT-4o API | 数据不出本地是红线 | ✅ `ai_engine.py` via `openai.AsyncOpenAI(base_url=...)` |
| **ADR-02** | 前后端分离，REST API | 前端 Vue3，后端 FastAPI | 服务端渲染 | SPA 交互复杂 | ✅ 11 route modules |
| **ADR-03** | 异步审查用 Celery | 2–5 分钟耗时 | BackgroundTasks | 需重试/状态查询 | ✅ `ai_review_tasks.py` `max_retries=3` |
| **ADR-04** | ORM 选 SQLAlchemy 2.0 | 团队经验 | Tortoise ORM | Alembic 标配 | ✅ async session + 3 model files |
| **ADR-05** | 数据库选 MySQL 8 | async 驱动兼容性 | PostgreSQL | `asyncmy` 零配置 | ✅ `mysql+asyncmy://` |
| **ADR-06** | 合同编号 `CON-YYYYMM-XXXX` | 按月重置 | UUID | 便于沟通 | ✅ `_generate_contract_no()` |
| **ADR-07** | 软删除用 `status="deleted"` | 审计追溯 | `deleted_at` | 与状态机统一 | ✅ `delete_contract()` |
| **ADR-08** | 审批流程 JSON 配置驱动 | 快速上线 | JSON 配置化 | **API 统一走 `approval_service.py` + `flow_config.json`；`workflow_service.py` 已删除** |
| **ADR-09** | AI 审查五维并行 | 5 维度耗时 | 串行 | 并行缩短 60% | ✅ `asyncio.gather(*dimension_tasks)` |
| **ADR-10** | Vue3 前端独立重建 | 原型 6000+ 行不可复用 | 原型转 SFC | 结构差异大 | ✅ `frontend/src/` 空 |

### 4.2 已知的技术债

| 编号 | 技术债 | 影响 | 解决策略 |
|------|--------|------|---------|
| **TD-01** | Celery task `_call_ai_engine` 返回 mock 数据 | AI 审查不产生真实结果 | Sprint 4 优先级 |
| **TD-02** | Auth middleware 鉴权失败返回 None 而非 401 | 无 Token 也能访问 API | 修复 `AuthMiddleware._verify_request_token` |
| **TD-03** | 缺少 Alembic migration | 部署需手动建表 | `alembic revision --autogenerate` 一次生成 |
| **TD-04** | 前端 Vue3 未启动 | 69 个后端 API 无前端对接 | Sprint 0 优先启动脚手架 |
| **TD-05** | `counterparties` 模型未创建 | 合同创建时无相对方校验 | Sprint 1 补 |
| **TD-06** | MinIO upload 调用被注释 | 文件上传不工作 | Sprint 2 取消 `await storage.upload_file(...)` 注释并对接 MinIO API |
| **TD-07** | `user.py` 中 `relationship()` 未导入 `sqlalchemy.orm` | 访问关系字段运行时 NameError | 补 `from sqlalchemy.orm import relationship` |
| **TD-08** | `contract.py` 重复定义 `AIReview` / `RiskAlert` / `AuditLog` | 与 `ai_review.py` 同名注册到同一 Base，迁移可能冲突 | 清理 `contract.py` 中的重复定义 |

---

## 五、性能考量

### 5.1 AI 审查性能

| 指标 | 预估 | 备注 |
|------|------|------|
| 单维度 LLM 推理 | ~15–30 秒 | Qwen3.6 35B-4bit on M2 Max |
| 五维并行总耗时 | ~30–60 秒 | `asyncio.gather` 并行 |
| 条款切分 | ~1 秒 | 正则 + 正则分词 |
| 风险评分 | < 1 秒 | 纯计算 |
| **端到端（含 Celery 调度）** | ~1–3 分钟 | 单合同 |

### 5.2 数据库

| 查询场景 | 索引策略 | 预估 QPS |
|---------|----------|---------|
| 合同列表（分页+过滤） | `idx_status` + `idx_type` + `idx_creator` | ~100 |
| 审批待办 | `approval_flows.idx_status` + `idx_contract` | ~50 |
| AI 审查结果查询 | `ai_reviews.idx_contract` + `idx_risk_level` | ~20 |
| 审计日志 | `audit_logs.idx_user` + `idx_time` | ~100 |

### 5.3 前端

| 页面 | 预估加载时间 | 备注 |
|------|-------------|------|
| 列表页（分页 20 条） | < 500ms | API 一次请求 |
| 合同详情（含 AI 摘要） | < 1s | 并行请求详情+审查结果 |
| AI 审查报告页 | < 2s | 五维审查结果 JSON 较大 |

---

## 六、安全设计

| 安全层 | 实现 | 状态 |
|--------|------|------|
| **传输安全** | HTTPS (Nginx)，开发环境 HTTP | ⏳ Nginx 配好但无证书 |
| **认证** | JWT Bearer Token，`AuthMiddleware` + `get_current_user` 依赖 | ✅ 代码已实现 |
| **密码** | bcrypt (12 rounds)，`passlib` | ✅ |
| **授权** | RBAC — Role → Permission 映射，`check_permission` 依赖 | ⚠️ 依赖未在所有端点启用 |
| **操作审计** | `AuditMiddleware` 全链路记录，`audit_logs` 表 | ✅ |
| **数据加密** | 敏感字段 AES-256 | ❌ 未实现（V2） |
| **SQL 注入防护** | SQLAlchemy ORM 参数化 | ✅ |
| **文件安全** | MinIO 存储 + 文件哈希校验 | ⚠️ MinIO 集成未完成 |
| **CORS** | `ALLOWED_ORIGINS` 白名单 | ✅ |

---

## 七、部署架构

```
┌─────────────────────────────────────────┐
│  Docker Compose (docker-compose.yml)      │
│                                          │
│  nginx:80 ──▶ frontend:8080              │
│              ──▶ backend:8000             │
│                                          │
│  mysql:3306    redis:6379                │
│  minio:9000    minio-console:9001         │
│  celery-worker (独立进程)                │
└─────────────────────────────────────────┘
```

### 7.1 服务清单

| 服务 | 端口 | 用途 | Docker 镜像 |
|------|------|------|-------------|
| Nginx | 80 | 反向代理 | nginx:alpine |
| Backend | 8000 | FastAPI API | python:3.11 |
| Frontend | 8080 | Vue3 SPA | node:20 |
| MySQL | 3306 | 关系数据库 | mysql:8.0 |
| Redis | 6379 | Cache + Broker | redis:7-alpine |
| MinIO | 9000/9001 | 文件存储 + Console | minio/minio |
| Celery Worker | — | 异步任务 | python:3.11 |
| AI 模型 | 8000/v1 | Qwen3.6 LLM | Apple Silicon 本地 |

---

## 八、V2 扩展规划

| 模块 | V1 状态 | V2 计划 |
|------|---------|--------|
| 履约跟踪 | 仅 `status=executing` 占位 | 里程碑管理、到期自动提醒 |
| 电子签章 | 未集成 | 法大大 / 上上签 API 对接 |
| 多组织 | V2 预留 `org_id` 字段 | 集团-子公司数据隔离 |
| 流程设计器 | JSON 配置（3 种流程） | 拖拽可视化流程配置 |
| 移动端 | `mobile-approval-design.md` 已设计 | H5 审批 + 企微推送 |
| 数据脱敏 | 无视图 | 审计日志脱敏 + 数据加密 |

---

*文档维护者：Sisyphus*  
*下次更新：V2 规划启动时*
