# AI 与评审深度集成 — 实施计划

> 基于「AI 大模型在评审中的落地应用」分析 | 2026-05-25  
> **上位方案**：[ai-llm-contract-review-deep-scheme.md](./ai-llm-contract-review-deep-scheme.md)（大模型深度应用总体方案，必读）

## 目标

将 AI 从「Boolean 门禁 + 独立报告页」升级为「评审工作台可消费的结构化初筛」，并消除 Mock/真实路径的数据错觉。

---

## PR 拆分

### PR-1（P0）评审工作台消费 AI — **本迭代实现**

| 任务 | 改动 |
|------|------|
| 后端 workspace 返回 AI 摘要 + 条款 Top N | `review_service.get_review_workspace` |
| 前端展示风险等级、条款列表、跳转报告 | `ReviewWorkspaceView.vue` |
| 测试 | 扩展 workspace API 断言 |

**验收**：法务进入评审工作台可见 AI 风险分与高风险条款，可点「查看完整报告」。

---

### PR-2（P0）AI 门禁版本一致 — **本迭代实现**

| 任务 | 改动 |
|------|------|
| `_ensure_ai_gate` 校验 `ai_reviews.version_id == contracts.current_version_id` | `review_service.py` |
| 测试 `test_legal_with_stale_ai_rejected` | `test_api_reviews.py` |

**验收**：修订后未重跑 AI，法务提交返回 400「请重新触发 AI 审查」。

---

### PR-3（P0）提交时 AI 失败可感知 — **本迭代实现**

| 任务 | 改动 |
|------|------|
| 创建合同提交后 AI 失败 Warning，不 silent catch | `CreateContractView.vue` |

**验收**：MLX 未启动时用户看到明确提示，仍可继续审批流程。

---

### PR-4（P0）真实审查不再回退 DEMO 门禁 — **本迭代实现**

| 任务 | 改动 |
|------|------|
| MLX 路径生成 `summary.gates` | `runner.compute_gates_from_payload` |
| `latest-review` 仅 mock 时回退 DEMO_GATES | `ai_review.py` |

**验收**：`model_version != mock` 时 gates 来自引擎计算，非 DEMO。

---

### PR-5（P1）规则引擎 MVP → 见总体方案 Phase AI-1

| 任务 | 改动 |
|------|------|
| 预付款比例、金额阈值等 | `rule_engine.py`（从 runner 抽出） |
| checklist auto_detectable 项 | 消费 `review_checklists.json` |
| Mock 与 MLX 共用 | orchestrator 调用 |

**验收**：真实 MLX 报告含 `rule_violations`，与 Mock 字段一致；issue 含 `label_id`。

---

### PR-6（P1）字段 Schema 统一 → Phase AI-1

| 任务 | 改动 |
|------|------|
| 统一 `AiReviewIssue` JSON Schema | orchestrator 输出 |
| 前端 `DIMENSION_LABELS` + label 筛选 | `ai-review.ts` / `AiReviewView` |

---

### PR-7（P2）法务确认 AI → Phase AI-2

| 任务 | 改动 |
|------|------|
| `POST /ai-review/{id}/confirm` → `reviewed` | API + 工作台 |
| 逐条 issue `human_status` | `ai_review_issues` 表 |

---

### PR-8（P2）AI → RiskAlert → Phase AI-3

| 任务 | 改动 |
|------|------|
| high/critical 自动预警 | review 完成 hook |

---

## 依赖关系

```text
PR-1 ─┬─ PR-6（字段统一后可增强展示）
PR-2 ─┤
PR-3 ─┤ 可并行
PR-4 ─┴─ PR-5（规则与门禁可合并迭代）
PR-7、PR-8 依赖 PR-1～4 稳定
```

---

## 本迭代交付范围

PR-1 ～ PR-4（P0 四项）**已完成**。后续按 [ai-llm-contract-review-deep-scheme.md](./ai-llm-contract-review-deep-scheme.md) Phase AI-1 起迭代。
