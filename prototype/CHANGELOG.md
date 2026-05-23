# 原型变更日志

## 2026-05-18（与 design 文档对齐 0.5.0）

- `roleConfig`：法务/财务移除 `approvals`，与 permission-matrix §3 一致
- `page-create`：合同类型增加 `other`
- `_click-test.mjs`：`ROLE_PAGES` 与 `visiblePages` 同步
- 设计文档：DESIGN_STATUS 0.5.0、permission-matrix 1.3、侧栏文案统一为「审查报告」等

## 2026-05-18（导航与权限对齐文档）

- 侧栏固定 **17** 项；`approval-history` 改为合同下钻（无侧栏菜单）
- `switchRole`：原型展示全部菜单，无权限项 `nav-restricted`（🔒），不 `display:none`
- 对齐 `docs/design/DESIGN_STATUS.md` 0.4.0、`docs/design/permission-matrix.md` §3～§4

## 2026-05-18（模块化 + 缺陷修复）

- 拆分为 `css/`、`js/`（4 模块）、`pages/`（20 页）、`partials/`
- 新增 `build.py` 合并生成 `index.html`（约 4000 行，原 6600+ 行）
- 修复：exportAuditLog / addAuditLog、合同字段归一化、重复函数、双存储、简易流程 Tab、黑名单提示、引导仅首次

## 2026-05-18（Phase C 准备）

- 新增 design-freeze-pre-review、development-kickoff、CR 模板
- 完善 design-freeze-confirmation 预填与遗留项

## 2026-05-18（Phase D）

- 新增 field-dictionary、api-page-mapping、prd-v1-checklist、permission-matrix
- 修复相对方下拉多余闭合标签

## 2026-05-18（设计对齐 V1.1）

- 待办审批：退回、委托（示意）
- AI 审查：疑似/不确定置信度样例；误报/漏报标记
- 提交合同：流程匹配弹窗
- 样例数据：DEMO-01/03/05
- 模板：待发布审批行；废止函数
- 用户页：filterUsers 修复
