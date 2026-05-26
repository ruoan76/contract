# AI 审查诊断报告

- **审查 ID**: REV-20260526131721-e54b71a7
- **风险**: medium / 49.5
- **完整度**: partial
- **分段数**: 3
- **失败维度**: 无
- **Critical 保底**: None

## 管线统计
- （旧记录无 pipeline_stats）

## Issue 分布
- 摘要 issue_count: 64
- clause_reviews 条数: 48
- issues_total: 64
- 已截断: False
- 风险等级: {"critical": 2, "high": 13, "medium": 33}
- 来源: {"llm": 35, "rule": 1, "rag": 12}

## 五维状态
- compliance: status=ok score=75.0
- risk: status=ok score=65.0
- financial: status=ok score=65.0
- capability: status=ok score=75.0
- anomaly: status=failed score=0.0

## 门禁
- gate_validity: warn — 清单效力项 4 项未通过
- gate_subject: pass — 甲方：甘肃省烟草公司兰州市公司；乙方：浪潮软件股份有限公司
- gate_clause: fail — 60 项条款风险待处理
- gate_consistency: warn — 形式/一致性检查见规则项
- gate_output: warn — 审查未完整完成，请法务重点复核
