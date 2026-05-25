#!/usr/bin/env bash
# 启动 MLX-LM OpenAI 兼容 API（本地 Qwen，供合同 AI 审查调用）
# 若本机已有 mlx_lm.server，勿重复启动；用 ps/lsof 查端口并写入 AI_BASE_URL
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="${ROOT}/backend"

MODEL="${AI_MODEL:-mlx-community/Qwen3.6-35B-A3B-4bit}"
HOST="${AI_MLX_HOST:-127.0.0.1}"
# 默认 27366：与本机常驻 MLX 一致；可通过 AI_MLX_PORT 覆盖
PORT="${AI_MLX_PORT:-27366}"

if [[ -f "${BACKEND}/.venv/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "${BACKEND}/.venv/bin/activate"
elif [[ -f "${ROOT}/.venv/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "${ROOT}/.venv/bin/activate"
fi

if ! python -c "import mlx_lm" 2>/dev/null; then
  echo "未找到 mlx-lm，请在 backend 虚拟环境中安装依赖："
  echo "  cd backend && pip install -r requirements.txt"
  exit 1
fi

echo "MLX 推理服务: ${MODEL}"
echo "监听: http://${HOST}:${PORT}/v1  (与 AI_BASE_URL 一致)"
echo "按 Ctrl+C 停止"
echo ""

exec python -m mlx_lm.server \
  --model "${MODEL}" \
  --host "${HOST}" \
  --port "${PORT}"
