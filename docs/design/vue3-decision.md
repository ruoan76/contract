# Vue3 启动决策（V1 联调后评估）

> 版本：1.0.0 | 日期：2026-05-19  
> 触发条件：V1 均衡推进计划 A-4（第 2 周末）

---

## 背景

| 层 | 现状 |
|----|------|
| `prototype/` | 20 页 UI + 147 项 Mock 测试全绿；已接入真实 API（`USE_REAL_API` + `api-*.js`） |
| `frontend/` | Vite + Vue3 空脚手架，无业务页面 |
| 后端 | 166 pytest + 10 integration；OpenAPI / Postman 已导出 |

DEMO-01～05 已通过 `prototype/_api-demo-test.mjs` 对真实后端跑通全链路。

---

## 决策：**Vue3 延后至 V1.1**

### 理由

1. **演示目标已满足**：原型 + API 层可在浏览器/控制台完成 DEMO-01～05，无需重写 20 页即可验证契约与流程。
2. **成本/收益**：全量 Vue3 重写约 2–3 周，当前瓶颈是「联调与部署验证」，而非组件框架。
3. **可复用资产**：`prototype/js/api-client.js` 等逻辑可直接迁移为 `frontend/src/api/` 模块；类型可由 `backend/openapi.json` 生成。
4. **风险可控**：原型 `USE_REAL_API=false` 保持 147 测回归；真实联调与 Mock 双轨并行。

### 何时启动 Vue3（V1.1 触发条件）

满足以下 **任一** 项即启动 `frontend/` 业务开发：

- 需要 **RBAC 路由级权限**、多租户或复杂状态管理（Pinia + 路由守卫）
- 需要 **性能优化**（虚拟列表、大列表分页、SSR/预渲染）
- 产品要求 **脱离原型** 的正式 UI/设计系统交付
- 原型维护成本超过 Vue3 增量开发（页面 >25 或多人并行前端）

### V1.1 启动清单（预置）

1. 从 OpenAPI 生成 TS 类型（如 `openapi-typescript`）
2. 迁移 `api-client` / `api-auth` 至 `frontend/src/api/`
3. 按侧栏 17 项优先级：P0 页（dashboard、create、contracts、approvals、review-workspace、seal）先行
4. 保留 `prototype/` 作为联调参考直至 Vue3 P0 页覆盖 DEMO-01

---

## 结论

**Vue3 前端已于 2026-05-19 启动**（`frontend/` Vite + Vue3 + Element Plus）。原型 `prototype/` **冻结为设计参考**，不再改动。

| 阶段 | 状态 |
|------|------|
| Phase 0 脚手架 | 完成 |
| Phase 1 API 层 | 完成（迁移自 prototype/js/api-*.js） |
| Phase 2 壳层 + RBAC | 完成 |
| Phase 3 DEMO-01 | 完成（create/approvals/review-workspace/seal） |
| Phase 4 DEMO-02~05 | 完成（counterparties/revision/ai-review/archives/config） |
| Phase 5 部署 | Dockerfile + nginx + CI |

**运行：** `cd frontend && npm run dev` → http://localhost:8080（需 backend :8000 + seed）
