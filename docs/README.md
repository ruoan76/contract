# 项目文档索引

> 合同审批管理平台 · 文档按用途分目录，便于评审与维护。

## 目录结构

| 目录 | 用途 | 评审入口 |
|------|------|----------|
| **[design/](./design/)** | **正式设计文档**（冻结、PRD、API、库表、权限、演示脚本） | [DESIGN_STATUS.md](./design/DESIGN_STATUS.md) |
| [reference/](./reference/) | 专题设计参考（流程/评审/模板等深度说明） | 按需查阅 |
| [archive/](./archive/) | 历史审计与评审报告（**Superseded**，勿作验收依据） | — |
| [plans/](./plans/) | 实施方案、Sprint 计划 | — |

高保真原型：`../prototype/index.html`

---

## 快速入口

1. **设计评审 / 冻结会** → [design/README.md](./design/README.md)
2. **开发启动** → [design/development-kickoff.md](./design/development-kickoff.md)
3. **15 分钟演示** → [design/demo-script-v1.md](./design/demo-script-v1.md)
4. **权限与导航** → [design/permission-matrix.md](./design/permission-matrix.md)

---

## 维护约定

- 影响范围、页面、状态、流程的变更：**先更新** `design/DESIGN_STATUS.md` 版本号与变更日志。
- 同步检查 [prototype/](../prototype/)：`01-data.js`（`visiblePages`）、`shell.html`（侧栏）、`build.py` 产物、`_click-test.mjs`。
- 正式设计文档只放在 `design/`；过程性审计完成后移入 `archive/` 并标注 Superseded。
- 专题长文放在 `reference/`，在 `DESIGN_STATUS` 或 `prd` 中交叉引用即可。
