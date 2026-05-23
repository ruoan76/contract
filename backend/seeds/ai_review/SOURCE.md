# 数据来源与许可

| 项 | 内容 |
|----|------|
| 上游仓库 | [CSlawyer1985/contract-review-pro](https://github.com/CSlawyer1985/contract-review-pro) |
| 上游版本 | V3.0（`crp-v3.0`，2026-05） |
| 许可协议 | **MIT License** |
| 作者 | 陈石 / CSlawyer1985 |

## 说明

本目录 `raw/*.csv` 与 `generated/*.json` 由上游 `data/` 目录衍生，用于本平台 AI 审查规则引擎与 RAG 种子数据，**不包含** Claude Skill 运行时。

生成命令：

```bash
python3 backend/seeds/ai_review/import_contract_review_pro.py
```

设计文档：

- [docs/reference/contract-review-pro-seeds.md](../../../docs/reference/contract-review-pro-seeds.md)
- [docs/design/ai-review-design.md](../../../docs/design/ai-review-design.md) §2.3

## 署名要求（MIT）

分发或改编 `generated/` 数据时，请保留本文件及上游仓库链接。
