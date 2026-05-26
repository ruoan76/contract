#!/usr/bin/env bash
# Celery AI 审查全链路验收脚本
# 用法：在 backend 目录执行 ./scripts/verify_celery_ai_review.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API_BASE="${API_BASE:-http://127.0.0.1:8000/api/v1}"
TOKEN="${TOKEN:-}"
TIMEOUT_SEC="${TIMEOUT_SEC:-600}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"

if [[ -z "$TOKEN" ]]; then
  echo "请先设置 TOKEN（Bearer JWT），例如：export TOKEN=\$(curl -s ... | jq -r .data.access_token)"
  exit 1
fi

auth_header=(-H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json")

echo "==> 创建测试合同"
create_resp=$(curl -sf "${auth_header[@]}" -X POST "${API_BASE}/contracts/" \
  -d '{"title":"Celery验收","contract_type":"purchase","counterparty_name":"供应商","amount":200000,"content":"预付款 35%，争议提交仲裁"}')
contract_id=$(echo "$create_resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")

echo "==> 触发 AI 审查 (AI_REVIEW_MOCK=0 AI_REVIEW_SYNC=0 需在服务端配置)"
review_resp=$(curl -sf "${auth_header[@]}" -X POST "${API_BASE}/ai-review/review" \
  -d "{\"contract_id\": ${contract_id}}")
review_id=$(echo "$review_resp" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['review_id'])")
echo "review_id=${review_id}"

deadline=$((SECONDS + TIMEOUT_SEC))
status=""
while (( SECONDS < deadline )); do
  latest=$(curl -sf "${auth_header[@]}" "${API_BASE}/ai-review/contracts/${contract_id}/latest-review")
  status=$(echo "$latest" | python3 -c "import sys,json; d=json.load(sys.stdin).get('data') or {}; print(d.get('review_status',''))")
  completeness=$(echo "$latest" | python3 -c "import sys,json; d=json.load(sys.stdin).get('data') or {}; print(d.get('review_completeness') or (d.get('summary') or {}).get('review_completeness',''))")
  echo "  status=${status} completeness=${completeness}"
  if [[ "$status" == "ai_done" ]]; then
    break
  fi
  if [[ "$status" == "failed" ]]; then
    echo "审查失败"
    exit 1
  fi
  sleep "$POLL_INTERVAL"
done

if [[ "$status" != "ai_done" ]]; then
  echo "超时：${TIMEOUT_SEC}s 内未 ai_done"
  exit 1
fi

if [[ -z "$completeness" ]]; then
  echo "缺少 review_completeness 字段"
  exit 1
fi

issues=$(curl -sf "${auth_header[@]}" "${API_BASE}/ai-review/${review_id}/issues")
count=$(echo "$issues" | python3 -c "import sys,json; print(len(json.load(sys.stdin)['data']['items']))")
if (( count < 1 )); then
  echo "issues 数量为 0"
  exit 1
fi

echo "==> 验收通过：ai_done completeness=${completeness} issues=${count}"
