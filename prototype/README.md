# 合同审批管理平台 — 高保真原型

## 目录结构

```text
prototype/
├── index.html          # 构建产物（可直接双击或用静态服务打开）
├── build.py            # 合并源码 → index.html
├── css/main.css        # 全局样式
├── js/
│   ├── 00-core.js      # 存储、Toast、审计、黑名单、自动保存
│   ├── 01-data.js      # 样例合同、角色配置
│   ├── 02-app.js       # 页面交互逻辑
│   └── 99-init.js      # 启动初始化
├── pages/              # 各页面 HTML 片段（20 页）
├── partials/modals.html
└── src/shell.html      # 壳：侧栏、顶栏、Toast
```

## 开发流程

1. 编辑 `pages/*.html`、`js/*.css`、`partials/` 等模块文件  
2. 运行合并：

```bash
cd prototype && python3 build.py
```

3. 用浏览器打开 `index.html`（建议本地静态服务以避免部分浏览器限制）：

```bash
python3 -m http.server 8765
# 访问 http://localhost:8765/
```

## 数据存储

- 主数据：`localStorage['contract_proto']`（合同列表、角色、待办数）  
- 草稿：`contract-draft`  
- 审计日志：`contract_audit_logs`  
- 黑名单：`counterparty_blacklist`

## 与正式设计文档对齐

| 设计文档 | 原型对应 |
|----------|----------|
| [DESIGN_STATUS §3](../docs/design/DESIGN_STATUS.md) | 20 页 = 17 侧栏 + 3 下钻；分组与文案见 §3.1 |
| [permission-matrix §3](../docs/design/permission-matrix.md) | `js/01-data.js` → `roleConfig.visiblePages`；`switchRole()` 打 🔒 |
| [data-dictionary](../docs/design/data-dictionary.md) | 合同类型下拉、`flowType` 样例合同 |
| [demo-script-v1](../docs/design/demo-script-v1.md) | DEMO-01～05 演示路径 |
| [api-page-mapping](../docs/design/api-page-mapping.md) | 页面 ID ↔ 规划 API |

变更页面/角色/权限时：**先改** `docs/design/`，再改 `01-data.js` / `shell.html`，并运行 `build.py` 与下方回归脚本。

## 回归测试

在本地启动静态服务后执行（需 `npm install` 安装 puppeteer）：

```bash
cd prototype
python3 build.py
python3 -m http.server 8765   # 另开终端
node _run-tests.mjs           # 结构审计 62 项 + E2E 147 项
```

分步：`node _page-audit.mjs` · `node _e2e-test.mjs`（或 `_click-test.mjs`）

| 脚本 | 用途 |
|------|------|
| `_test-lib.mjs` | 公共常量、Runner、Puppeteer 辅助 |
| `_page-audit.mjs` | HTML 平衡、非嵌套、标题映射 |
| `_e2e-test.mjs` | P0/P1/P2、RBAC、Demo、数据一致性 |
| `_run-tests.mjs` | 一键 audit + e2e |

环境变量：`PROTO_URL`、`TEST_DELAY`。缺 Chrome：`npx puppeteer browsers install chrome`

## 角色与菜单（原型 vs 正式环境）

- **原型**：侧栏 **17 个菜单全部显示**；当前角色无权限的项显示为半透明 + 🔒，仍可点击进入便于 UI 走查。
- **正式环境**：无权限菜单不展示，见 [permission-matrix](../docs/design/permission-matrix.md) §3、§4。
- 顶栏 **6 个角色**（无独立「高管」项）；高管审批在 `review-workspace` 高管 Tab 演示（见 DESIGN_STATUS §3.4）。

## 设计文档

正式设计文档目录：[../docs/design/](../docs/design/README.md)（评审入口：[DESIGN_STATUS](../docs/design/DESIGN_STATUS.md)）

## 演示脚本

见 [../docs/design/demo-script-v1.md](../docs/design/demo-script-v1.md)
