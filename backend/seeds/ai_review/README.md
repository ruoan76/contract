# AI 审查种子数据

从 [contract-review-pro](https://github.com/CSlawyer1985/contract-review-pro)（MIT）导入的结构化规则与模板，供审查编排、规则引擎与 RAG 使用。

## 目录

| 路径 | 说明 |
|------|------|
| [SOURCE.md](./SOURCE.md) | 许可与上游版本 |
| [raw/](./raw/) | 上游 CSV 快照（可 `curl` 更新） |
| [import_contract_review_pro.py](./import_contract_review_pro.py) | CSV → JSON 生成脚本 |
| [generated/](./generated/) | 提交到仓库的 JSON 产物 |

## 快速使用

```bash
# 重新生成 JSON（修改 raw/ 或映射表后）
python3 backend/seeds/ai_review/import_contract_review_pro.py

# 查看条目数
python3 -c "import json; from pathlib import Path; m=json.loads(Path('backend/seeds/ai_review/generated/manifest.json').read_text()); print(m)"
```

## 产物清单

| 文件 | 用途 |
|------|------|
| `risk_labels.json` | 15 风险标签 → 报告分组 / `label_id` |
| `revision_routing.json` | 修订方式路由 → `revision_method` |
| `review_checklists.json` | 53 项审查清单（含 `auto_detectable`） |
| `contract_type_map.json` | 平台 7 类 ↔ 上游 profile |
| `contract_type_profiles.json` | 30 类审查要点 |
| `risk_templates.purchase.json` | 买卖/通用风险模板子集 |
| `manifest.json` | 版本与计数 |

实现期在应用启动或迁移中加载 `generated/*.json` 写入数据库（表结构见设计文档）。
