# MLX 本地开发（Qwen + 合同 AI 审查）

在 Apple Silicon 上使用 **mlx-lm** 启动 OpenAI 兼容 API，后端通过 `AIReviewEngine` 调用本地 Qwen 完成五维审查。

## 本机端口（先探测再配置）

**不要假设 MLX 在 8000。** 先用下面命令看实际端口：

```bash
# 查看 mlx_lm.server 进程与端口
ps aux | grep mlx_lm.server | grep -v grep
lsof -nP -iTCP -sTCP:LISTEN | grep -E 'mlx|27366'

# 验证 OpenAI 兼容 API
curl -s http://127.0.0.1:<MLX端口>/v1/models | head
```

### 当前开发机实测（2026-05-25）

| 服务 | 地址 | 说明 |
|------|------|------|
| MLX-LM | `http://127.0.0.1:27366/v1` | `mlx_lm.server` 已常驻，模型 Qwen3.6-35B-A3B-4bit |
| 合同 FastAPI | `http://127.0.0.1:8000` | 与 `frontend/vite.config.ts` 的 `/api` 代理一致 |
| 合同前端 Vite | `http://127.0.0.1:8080` | 浏览器访问入口 |
| 已占用勿用 | 8088, 8765, 5173 | 其他项目 |

`backend/.env` 已按上表生成（gitignore，不提交）。

## 1. 安装依赖

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 环境变量

```bash
cp .env.mlx.example .env
# 若 MLX 端口变化，只改 AI_BASE_URL
```

推荐配置：

```bash
PORT=8000
AI_REVIEW_MOCK=0
AI_REVIEW_SYNC=1
AI_BASE_URL=http://127.0.0.1:27366/v1
AI_MODEL=mlx-community/Qwen3.6-35B-A3B-4bit
AI_MAX_TOKENS=2048
```

| 变量 | 含义 |
|------|------|
| `AI_REVIEW_MOCK=1` | 演示数据（默认） |
| `AI_REVIEW_MOCK=0` | 调用真实 MLX |
| `AI_REVIEW_SYNC=1` | 同步审查，无需 Celery（本地推荐） |

## 3. MLX 服务

若本机 **已有** `mlx_lm.server`（如 27366），无需再启动。

需要新起实例时：

```bash
./scripts/start-mlx-server.sh
# 或指定端口：AI_MLX_PORT=27366 ./scripts/start-mlx-server.sh
```

## 4. 启动后端 + 前端

```bash
# 终端 1 — 后端（8000）
cd backend && source .venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# 终端 2 — 前端（8080，代理 /api → 8000）
cd frontend && npm run dev
```

浏览器打开：`http://127.0.0.1:8080`

## 5. 验证

```bash
curl -s http://127.0.0.1:27366/v1/models | head
curl -s http://127.0.0.1:8000/health
```

前端：合同 →「AI 报告」→「触发审查」。

## 6. 相关代码

- 引擎：`app/services/ai_review/ai_engine.py`
- 执行器：`app/services/ai_review/runner.py`
- 配置：`app/core/config.py`
