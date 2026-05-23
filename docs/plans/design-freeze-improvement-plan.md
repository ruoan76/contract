# 合同审批管理平台 — 设计完善与冻结方案

> 版本：**V1.1** | 日期：2026-05-18 | 阶段：设计 + 原型迭代  
> 依据：[检查结论摘要](../design/design-freeze-audit-summary.md) | [方案评审记录](#十二方案评审记录)  
> 目标：在**不写业务代码**前提下，完成文档自洽、原型补齐、设计冻结，为 V1 开发提供单一真相源。  
> **评审结论**：有条件通过（V1.1 已吸收评审意见）

---

## 一、方案总览

### 1.1 核心目标

| 目标 | 验收标准（可度量） |
|------|-------------------|
| **文档自洽** | 核心文档无 PostgreSQL/22 页/parties 等矛盾；4 份旧审计已 Superseded |
| **原型可演示** | `demo-script-v1.md` 15 分钟内走完 DEMO-01～05；无阻断性死链 |
| **设计可冻结** | `DESIGN_STATUS.md` 为唯一入口；§二 冻结决策表全部闭合 |
| **开发可启动** | `prd-v1-checklist` P0 满足率 ≥95%（见 §九 公式）；字段字典 + API 映射交付 |

### 1.2 工作包与依赖

```text
Phase A（文档收敛）  3～4 天
    │
    ├── A-5 workflow-vs-review ──┐
    ├── A-6 status 字典 ─────────┼──► Phase B（原型补齐）5～7 天
    └── DESIGN_STATUS ───────────┘         │
                                           ▼
                              Phase C（预评审 + 冻结会）2～3 天
                                           │
                                           ▼
                              Phase D（开发交接）1～2 天
```

| 阶段 | 工期 | 说明 |
|------|------|------|
| Phase A | 3～4 天 | 消除文档冲突、闭合冻结决策 |
| Phase B | 5～7 天 | **B-2 依赖 A-5 定稿**；可与 A 后半段并行 |
| Phase C | 2～3 天 | 含预评审 30min + 正式冻结会 |
| Phase D | 1～2 天 | 规格制品，不写业务代码 |

**总工期**：

| 配置 | 周期 | 适用 |
|------|------|------|
| 推荐 | **3 周** | 1 人兼产品+原型，或需法务/财务多轮对齐 |
| 紧凑 | 2～2.5 周 | 2 人并行（文档 + 原型），决策 48h 内闭合 |

### 1.3 不在本方案范围

- 后端 FastAPI 实现、数据库迁移、前端 Vue 工程搭建  
- **`backend/` 目录**：设计阶段**不维护、不修复**；冻结后开发按 `api-spec` 重建或移除误导骨架（写入 DESIGN_STATUS）  
- V2：移动端 H5、履约里程碑、电子签章、多组织、会签、审批委托（生产实现）  
- AI 模型训练、法规库生产部署、`ai-review-design.md` 全文落地（见 §2.6）

---

## 二、冻结决策表（V1.1 已闭合）

> 写入 `DESIGN_STATUS.md` §冻结决策；变更须升版本并记录。

| ID | 决策项 | V1.1 定稿 | 理由 |
|----|--------|-----------|------|
| **D1** | `pending` vs `reviewing` | **合并**：仅保留 `status=pending`，子阶段用 `approval_status` | 实现简单，与原型「待审批」文案一致 |
| **D2** | 相对方数据模型 | **独立 `counterparties` 表** + `contracts.counterparty_id` + 快照字段 | 与 PRD、原型、相对方页一致 |
| **D3** | 简易流程法务节点 | **进入 `review-workspace`，仅开放法务 Tab**（无财务/高管） | 复用评审能力，避免第三套 UI |
| **D4** | 审批「委托」 | **V1 原型示意**：按钮 + Toast「V1 仅示意，生产 V1.1」；PRD §3.5 委托降为 **P1** | 降低实现承诺，演示不缺失 |
| **D5** | 审批「会签」 | **V1 不做**；PRD 会签降为 **P2**；`config` 可保留文案 | 避免与 B-1 范围冲突 |
| **D6** | AI 误报/漏报 | **冻结演示必做**（原可选升为 B-4 **P0-demo**） | AI 差异化演示核心 |
| **D7** | 独立风险/统计页 | **V1 不建** `page-risk` / `page-statistics` | 功能合并至现有页 |

---

## 三、Phase A — 文档收敛

### 3.1 新增：`docs/design/DESIGN_STATUS.md`（唯一真相源）

**章节清单**：

1. 版本、变更日志  
2. V1 范围（§八 镜像）  
3. **冻结决策表**（§二 镜像）  
4. 页面清单（20 页）：ID、名称、侧栏/下钻、角色、`visiblePages`（正式环境）、原型全菜单（D9）、PRD 章节  
5. 状态枚举（引用 `contract-status-dictionary.md`）  
6. 技术栈：MySQL 8、Redis、MinIO、FastAPI、Vue3（规划）  
7. 已知缺口登记表  
8. 文档索引 + Superseded 列表  
9. **`backend/` 说明**：设计阶段不维护  

**工期**：1 天 | **验收**：项目组回复「以 DESIGN_STATUS 为准」

---

### 3.2 文档修订任务

| 序号 | 文件 | 修改内容 | 优先级 |
|------|------|----------|--------|
| A-1 | `README.md` | PostgreSQL → **MySQL 8**；`frontend/` 标注规划 | P0 |
| A-2 | `docs/design/prd.md` | §3.7 履约统一 **V2**；§4.2 对齐 mobile 文档；**委托 P1、会签 P2** | P0 |
| A-3 | `docs/design/database-design.md` | **补全 `counterparties` DDL**；`contracts.counterparty_id`；ER 图更新 | P0 |
| A-4 | `docs/design/design-alignment-requirements.md` | 20 页已实现 + 2 不建；`page-create` 命名 | P0 |
| A-5 | `docs/design/workflow-vs-review.md` | 双轨流程定稿（§3.3） | P0 |
| A-6 | `docs/design/contract-status-dictionary.md` | 四套枚举 + Mermaid 状态机；**采纳 D1** | P0 |
| A-7 | `docs/design/api-spec.md` | v1.1 变更说明；状态与字典对齐；V2 端点标注 | P1 |
| A-8 | 4 份过期审计 | 文首 `Superseded → DESIGN_STATUS` | P1 |
| **A-9** | `DESIGN_STATUS` + `ai-review-design.md` 文首 | 标明：**AI 设计文档 = 开发蓝图，≠ V1 原型范围** | P0 |
| **A-10** | `docs/design/data-dictionary.md`（新建） | `contract_type` vs `template_category` 字典 | P1 |

**Superseded**：`comprehensive-design-review.md`、`prototype-completeness-audit.md`、`p0-p1-completion-report.md`（历史保留）；`design-alignment-requirements.md` 部分章节

---

### 3.3 `workflow-vs-review.md` 定稿（V1.1）

```text
【标准流程 — 评审驱动】
触发：金额 ≥ 类型阈值（见 config）或采购/销售非简易档
路径：起草 → 提交 → AI(ai-review) → 法务(review-workspace/legal)
     → 财务(finance，按金额) → 高管(executive，按金额)
     → [董事会 board，仅特殊流程] → 用印(seal) → 归档(archives)

【简易流程 — 审批 + 法务快审】
触发：金额 < 简易阈值
路径：起草 → 提交 → AI → 部门主管(approvals)
     → 法务(review-workspace，仅 legal Tab) → 用印 → 归档

【退回】
任一节点的「退回」→ revision-workspace → 再提交
AI 重跑：config 可配（原型用勾选示意）

【职责边界】
- approvals：部门主管等业务审批节点
- review-workspace：法务/财务/高管专业评审
- 最终法律责任：法务评审意见；经营决策：高管批准
```

**验收**：产品、法务、财务、开发**四方**签字（邮件即可）。

---

### 3.4 `contract-status-dictionary.md`（采纳 D1）

**`contracts.status`（V1 冻结，无 `reviewing`）**：

| 值 | 中文 | 可编辑 | 下一典型状态 |
|----|------|--------|--------------|
| `draft` | 草稿 | 是 | `pending` |
| `pending` | 流程中 | 否 | `approved` / `draft`（退回） |
| `approved` | 已通过 | 否 | `sealed` |
| `sealed` | 已用印 | 否 | `signed` |
| `signed` | 已签署 | 否 | `archived` |
| `archived` | 已归档 | 否 | — |
| `executing` | 执行中 | 否 | 看板展示，无履约子模块 |
| `terminated` | 已终止 | 否 | — |
| `void` | 已作废 | 否 | — |

**`contracts.approval_status`（子阶段，流程进行时必填）**：

`ai_screening` → `dept_approval` → `legal_review` → `finance_review` → `executive_approval` → `board_approval` → `seal_pending` → `done`

**另册**：`ai_review.status`、`review_record.stage` 在同文件 §3～§4 定义。

---

### 3.5 `counterparties` 表（采纳 D2）

完整 DDL 写入 `database-design.md`；`contracts` 增加 `counterparty_id`，保留 `counterparty_name`、`counterparty_credit_code` 快照。

---

### 3.6 AI 设计文档范围说明（A-9）

| 文档 | V1 原型 | V1 开发 |
|------|---------|---------|
| `ai-review-design.md` Skill/RAG/Chroma | 不实现 | 分 Sprint 落地 |
| 原型 `ai-review` | 五维度报告 + 置信度 + 规则文案 | 对齐即可 |
| 法规 50 条 | 示例引用 3～5 条 | 开发期导入 |

---

## 四、Phase B — 原型补齐

### 4.1 任务清单（含优先级调整）

| 序号 | 页面 | 变更 | 优先级 | 依赖 |
|------|------|------|--------|------|
| B-1 | `approvals` | **退回**（实装）；**委托**（示意 + DESIGN_STATUS 登记） | P0 | — |
| B-2 | `create` | 提交弹窗：**匹配流程** + 节点预览 | P0 | A-5 |
| B-3 | `ai-review` | 中置信 65%、低置信 52% 样例 + 「疑似」「需人工复核」标签 | P0 | — |
| B-4 | `ai-review` / `review-workspace` | **误报 / 漏报** 按钮（冻结演示必做） | **P0-demo** | — |
| B-5 | `templates` | 废止；「待发布审批」样例行 | P1 | — |
| B-6 | `contract-detail` | **版本历史** Tab | P1 | — |
| B-7 | 列表/历史 | 董事会流程：DEMO-03 合同样本 + `approval-history` 时间线 | P2 | — |
| B-8 | `users` | `filterUsers()` 修复 | P2 | — |
| B-9 | `counterparties` | 下拉 DOM 修复 | P2 | — |
| **B-10** | `messages` | 1 条「审批超时已升级」样例（24h/48h） | P1 | — |
| **B-11** | `mockContracts` | DEMO-01～05 写入 JS 常量区，与演示脚本一致 | P0 | A-5 |

**不建页（D7）**：`page-risk` → messages + contract-detail + ai-review；`page-statistics` → dashboard + review-center

---

### 4.2 演示数据包 DEMO-01～05

| ID | 场景 | 金额 | 流程 | 演示路径 |
|----|------|------|------|----------|
| DEMO-01 | 小额采购 | 8 万 | 简易 | create → approvals → seal |
| DEMO-02 | 标准采购 | 85 万 | 标准 | 四阶段 review-workspace |
| DEMO-03 | 重大采购 | 250 万 | 特殊+董事会 | config + 高管 + history 董事会节点 |
| DEMO-04 | 黑名单 | — | 拦截 | create 警告 → 法务强制复核 |
| DEMO-05 | AI 低置信 | 32 万 | 标准 | ai-review 疑似 → 误报/漏报演示 |

**实现**：`prototype/index.html` 内 `MOCK_CONTRACTS` 或扩展现有数组；编号与 `demo-script-v1.md` 一致。

---

### 4.3 原型交互规范

1. 禁止无 `onclick` 的按钮  
2. Toast 不作「未实现」占位；委托除外（须带「V1 示意」）  
3. 新页：若进侧栏则加入 `shell.html` + `ALL_NAV_PAGES`；下钻页仅 `switchPage` + 返回；`visiblePages` 管正式环境 RBAC，原型用 `nav-restricted` 示意  
4. 字段 id 对齐 `data-dictionary` / `api-spec`  
5. 冻结后：新建 `prototype/CHANGELOG.md` 记录每次演示相关变更  

---

## 五、Phase C — 设计冻结

### 5.1 预评审（Phase B 结束前）

| 项 | 内容 |
|----|------|
| 时长 | 30 min |
| 参与 | 产品 + 开发（+ 法务可选） |
| 内容 | 按 `demo-script-v1.md` 走一遍；记录阻断项 |
| 产出 | 阻断项清单，须在正式会前清零 |

### 5.2 正式冻结会

| 项 | 内容 |
|----|------|
| 时长 | 2h |
| 参与 | 产品、**法务（R）**、**财务（R）**、开发（R）、UI（C） |
| 议程 | ① DEMO 演示 20min ② 职责边界 15min ③ 状态/流程签字 20min ④ 遗留项 10min |
| 产出 | 《设计冻结确认单》 |

### 5.3 冻结确认清单

- [ ] `DESIGN_STATUS.md` v1.0+  
- [ ] §二 冻结决策表已闭合  
- [ ] `workflow-vs-review.md` 四方确认  
- [ ] `contract-status-dictionary.md` 定稿  
- [ ] `database-design.md` 含 counterparties  
- [ ] 原型 20 页 + B 项完成（P0 / P0-demo 必达）  
- [ ] PRD 修订（履约 V2、mobile、委托 P1、会签 P2）  
- [ ] **遗留项 ≤3**，均有负责人与目标版本  

### 5.4 冻结确认单（模板）

```markdown
# 设计冻结确认单
- 项目：合同审批管理平台 V1
- 冻结版本：DESIGN_STATUS v___
- 日期：____
- 参会：____

## 确认范围
- [ ] 20 页原型 + demo-script-v1
- [ ] workflow-vs-review 定稿
- [ ] contract-status-dictionary 定稿

## 遗留项（≤3）
| 项 | 负责人 | 目标版本 |
|----|--------|----------|
| | | |

## 签字
产品：____  法务：____  财务：____  开发：____
```

### 5.5 冻结后变更

1. 更新 `DESIGN_STATUS` patch 版本 + 变更日志  
2. PRD 与原型同步  
3. 开发期变更走 CR（模板后续补充）  

---

## 六、Phase D — 开发交接

| 交付物 | 路径 | 说明 |
|--------|------|------|
| 字段字典 | `docs/design/field-dictionary.md` | 表单 → DB → API |
| 页面-API 映射 | `docs/design/api-page-mapping.md` | 与 `api-spec` v1.1 **同批提交** |
| 状态机图 | `contract-status-dictionary.md` 内 Mermaid | — |
| 演示脚本 | `docs/design/demo-script-v1.md` | 15 min 逐步操作 |
| PRD P0 勾选 | `docs/design/prd-v1-checklist.md` | 可度量验收 |
| 权限矩阵 | `docs/design/permission-matrix.md` | 角色 × 页面 × 操作（无 UI） |
| 视觉基线（可选） | `docs/visual-baseline.md` | 沿用原型 CSS 变量 |

---

## 七、任务排期（推荐 3 周）

| 周 | 周一～周二 | 周三～周四 | 周五 |
|----|------------|------------|------|
| **W1** | A：DESIGN_STATUS + D1～D7 写入 | A：workflow + status 字典 + data-dictionary | A 收尾；**B-1、B-3、B-11** |
| **W2** | **B-2**（依赖 workflow）；B-4、B-10 | B-5、B-6；demo-script 初稿 | **预评审**；B-8、B-9 |
| **W3** | **正式冻结会** | D：字段字典 + API 映射 + prd checklist | 缓冲；开发 kickoff（可选） |

---

## 八、责任分工（RACI）

| 工作包 | 产品 | 法务 | 财务 | 开发 | UI |
|--------|------|------|------|------|-----|
| DESIGN_STATUS | A/R | C | I | C | I |
| 冻结决策 D1～D7 | A | C | C | C | I |
| workflow 定稿 | R | **R** | **R** | C | I |
| 原型 P0 | R | C | I | C | R |
| DEMO 数据 | R | C | C | I | I |
| 冻结签字 | A | **R** | **R** | **R** | C |

---

## 九、V1 范围边界

### 9.1 V1 必须做

起草四模式、模板库、相对方/黑名单、AI 报告（五维度+置信度+误报漏报演示）、评审闭环、审批退回、用印归档、看板、消息示意、用户/审计/配置、通知文案（可 mock）。

### 9.2 V1 明确不做

独立 risk/statistics 页、H5 应用、履约里程碑、电子签、多组织、流程设计器、ERP/OA/天眼查生产对接、**会签（D5）**、**委托生产实现（D4）**。

### 9.3 V1 可选

B-5 模板发布审批 UI、B-7 董事会列表行、`visual-baseline.md`。

---

## 十、验收标准

### 10.1 阶段验收

| 阶段 | 标准 |
|------|------|
| A | 无文档矛盾；DESIGN_STATUS 存在；§二 决策表已写入 |
| B | DEMO-01～05 可演示；`demo-script` 无阻断；P0 + P0-demo 完成 |
| C | 确认单签字；遗留 ≤3 |
| D | 字段字典 + api-page-mapping + prd-v1-checklist 交付 |

### 10.2 P0 满足率公式

```text
满足率 = (「已演示」条数 + 「V1不做」且 PRD 已修订条数) / PRD P0 总条数
冻结要求：满足率 ≥ 95%
```

`prd-v1-checklist.md` 每条标注：`已演示` | `V1不做` | `待补` | `V2`。

---

## 十一、风险与应对

| 风险 | 应对 |
|------|------|
| 审批/评审职责重叠 | 冻结会专设 15min 职责边界（§3.3） |
| 状态枚举膨胀 | D1 已合并 pending/reviewing |
| AI 文档期望过高 | A-9 范围说明 + 演示只承诺报告形态 |
| 原型 6580 行冲突 | `prototype/CHANGELOG.md` |
| 财务未参会 | RACI 财务对 DEMO-02/03、workflow 为 **R** |
| 无 UI 稿 | 可选 `visual-baseline.md` 提取 CSS 变量 |
| 旧审计误导 | A-8 Superseded |

---

## 十二、方案评审记录

| 项 | 内容 |
|----|------|
| 评审日期 | 2026-05-18 |
| 结论 | **有条件通过** → V1.1 已闭合 D1～D7 |
| 主要修订 | 决策表、A-9/10、B-10/11、3 周排期、预评审、量化验收、财务参会、AI/会签/委托范围 |

---

## 十三、附录

### 附录 A：PRD P0 与 Phase B 映射

| PRD | 状态 | Phase B |
|-----|------|---------|
| 3.1 起草 | ✅ | B-11 |
| 3.2 模板 | ✅ | B-5 |
| 3.3 相对方 | ✅ | B-9 |
| 3.4 AI | ⚠️ | B-3、B-4 |
| 3.5 审批 | ⚠️ | B-1、B-2、B-10；委托/会签改 PRD 优先级 |
| 3.6 用印 | ✅ | — |
| 3.8 归档 | ✅ | — |

### 附录 B：执行顺序（PR 建议）

1. `DESIGN_STATUS.md`  
2. `workflow-vs-review.md` + `contract-status-dictionary.md`  
3. `README`、`prd`、`database-design`、`data-dictionary`  
4. Superseded 标记  
5. 原型 B 项 + `demo-script-v1.md`  
6. Phase D 交付物  

### 附录 C：文档索引

| 文档 | 用途 |
|------|------|
| `docs/design/DESIGN_STATUS.md` | **唯一真相源（待建）** |
| `docs/plans/design-freeze-improvement-plan.md` | 本方案 |
| `docs/design/design-freeze-audit-summary.md` | 检查摘要 |
| `docs/design/ai-review-design.md` | 开发期 AI 蓝图 |
| `prototype/index.html` | 高保真原型 |

---

**立即执行（48h）**：① 创建 `DESIGN_STATUS.md` ② 创建 `workflow-vs-review.md` ③ 确认法务/财务评审 workflow 时间 ④ 启动 B-1、B-3、B-11。
