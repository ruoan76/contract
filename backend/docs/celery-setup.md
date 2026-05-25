# Celery + Qwen AI 审查部署指南

当 `AI_REVIEW_MOCK=0` 且 `AI_REVIEW_SYNC=0` 时，后端通过 Celery 异步 worker 调用本地 Qwen（MLX）。  
**本地开发更推荐** `AI_REVIEW_SYNC=1`（无需 Redis/Celery），见 [mlx-local-dev.md](./mlx-local-dev.md)。

## 前置依赖

| 组件 | 用途 | 默认地址 |
|------|------|----------|
| Redis | Celery broker / result backend | `redis://localhost:6379` |
| MySQL / SQLite | 业务数据库 | 见 `.env` 中 `DATABASE_URL` |
| Qwen (MLX) | 本地 LLM 推理 | `AI_BASE_URL` 与本机 `mlx_lm.server` 端口一致（见 [mlx-local-dev.md](./mlx-local-dev.md)） |

## 环境变量

```bash
# 关闭 mock，启用真实 AI 审查
AI_REVIEW_MOCK=0

# OpenAI 兼容 API（MLX-LM 或 vLLM 等）
AI_MODEL=mlx-community/Qwen3.6-35B-A3B-4bit
AI_BASE_URL=http://127.0.0.1:27366/v1
AI_API_KEY=local

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

合同解析 mock 独立控制：

```bash
AI_PARSE_MOCK=1   # 默认，启发式字段提取
AI_PARSE_MOCK=0   # 同样使用启发式，仅标记 mock=false
```

## 启动 Qwen 推理服务（示例：MLX-LM）

```bash
# 安装依赖（已在 requirements.txt）
pip install mlx mlx-lm openai

# 启动 OpenAI 兼容 API（端口 8000）
python -m mlx_lm.server \
  --model mlx-community/Qwen3.6-35B-A3B-4bit \
  --host 0.0.0.0 \
  --port 8000
```

> 模型路径与端口需与 `AI_BASE_URL` 一致。

## 启动 Celery Worker

在项目 `backend/` 目录：

```bash
# AI 审查队列 worker
celery -A app.celery_app worker \
  -Q ai_review,notifications,archive \
  -l info \
  --concurrency=2
```

可选 beat 调度（到期提醒等定时任务）：

```bash
celery -A app.celery_app beat -l info
```

## 启动 FastAPI

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

## 验证流程

1. 确认 Redis 可连接：`redis-cli ping` → `PONG`
2. 确认 Qwen API：`curl http://localhost:8000/v1/models`
3. 创建合同并 POST `/api/v1/ai-review/review`
4. 轮询 GET `/api/v1/ai-review/{review_id}/result` 直至 `status=ai_done`
5. 导出报告 GET `/api/v1/ai-review/{review_id}/report?format=pdf`

## 常见问题

- **审查一直处于 reviewing**：检查 Celery worker 是否运行、Redis 是否可达、worker 日志是否有异常。
- **503 AI 审查服务暂时不可用**：Celery task 派发失败，确认 `CELERY_BROKER_URL` 与 worker 队列名一致（`ai_review`）。
- **模型超时**：调大 `celery_app.conf.task_time_limit` 或减小 `AI_MAX_TOKENS`。

## 相关代码

- Celery 配置：`app/celery_app.py`
- 审查任务：`app/celery_tasks/ai_review_tasks.py`
- 审查引擎：`app/services/ai_review/ai_engine.py`
- Mock 开关：`app/core/config.py` → `AI_REVIEW_MOCK`
