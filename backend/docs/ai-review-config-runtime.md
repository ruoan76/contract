# AI 审查配置运行时说明

## 配置读取优先级

1. **已发布 DB 缓存**（`ConfigStore.refresh_config_cache`）：存在 `ai_config_versions.is_current=true` 且库内有启用中的清单项时，审查任务、Prompt、规则引擎、RAG 均读内存缓存。
2. **JSON 种子回退**：未 seed / 未发布 / 缓存为空时，清单/标签/路由/法条读 `backend/seeds/ai_review/generated/*.json` 与 `legal_snippets.json`。
3. **硬规则代码回退**：无 DB 缓存时，硬规则读 `config_seed.DEFAULT_HARD_RULES`（与 seed 导入目标一致）。

## 发布与草稿

- 规则中心 CRUD **直接写入业务表**；**新审查任务**在管理员执行 `POST /api/v1/ai-review/config/publish` 后通过 `refresh_config_cache` 生效。
- 未发布前：若进程内已有旧缓存，审查仍用旧版；若无缓存则用 JSON 回退（**DB 编辑不可见**）。
- `POST /config/import-seeds`：导入 JSON 并立即刷新缓存（等同导入即生效）。
- 前端规则中心用会话级 `hasUnpublishedEdits` 提示「待发布」；**不做** DB 与缓存的全局脏检测。

## 法条 CSV 导入

- `POST /api/v1/ai-review/config/legal-snippets/import-csv`（仅 admin）：上传 UTF-8（含 BOM）或 GBK 编码 CSV。
- 列：`snippet_id`（必填）、`keywords`（英文逗号/中文顿号分隔）、`text`（必填）、`enabled`（可选，默认 true）。
- 按 `snippet_id` **upsert** 写入 `ai_legal_snippets`；**不**调用 `refresh_config_cache`，与法条 CRUD 同为草稿，需发布后 RAG 才读新库。

## 停用规则

- `POST /config/disable-rule`：写库 `enabled=false` 后，若已有发布版本则**自动刷新缓存**，无需再次发布。

## 运维检查

```bash
cd backend
alembic upgrade head
python scripts/seed_ai_review_config.py
python scripts/verify_ai_review_seeds.py
```

启动日志出现 `AI 审查配置缓存已加载: <version>` 表示运行时走 DB；否则为 JSON 回退。

## 多 Worker

内存缓存不跨进程；发布或停用后需各 worker 各自刷新（当前单进程开发环境无此问题；生产多实例需后续引入广播或短 TTL）。
