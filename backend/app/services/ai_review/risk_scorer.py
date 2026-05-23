# -*- coding: utf-8 -*-
"""风险评分 — 基于条款审查结果计算综合风险分与报告。"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class RiskScore(BaseModel):
    """风险评分结果"""

    risk_score: float = Field(default=0.0, description="综合风险分 0-100")
    risk_level: str = Field(default="low", description="风险等级: low/medium/high/critical")
    dimension_scores: Dict[str, float] = Field(default_factory=dict, description="各维度得分")
    clause_scores: Dict[str, float] = Field(default_factory=dict, description="条款得分")
    critical_issues: List[dict] = Field(default_factory=list, description="关键问题列表")
    high_issues: List[dict] = Field(default_factory=list, description="高危问题列表")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="统计信息")


# ---------------------------------------------------------------------------
# 权重配置
# ---------------------------------------------------------------------------

_DIMENSION_WEIGHTS: dict[str, float] = {
    "compliance": 0.25,
    "risk": 0.30,
    "financial": 0.20,
    "capability": 0.15,
    "anomaly": 0.10,
}

_RISK_LEVEL_THRESHOLDS: list[tuple[float, str]] = [
    (90.0, "critical"),
    (70.0, "high"),
    (40.0, "medium"),
    (0.0,  "low"),
]

_SEVERITY_WEIGHTS: dict[str, float] = {
    "low": 5,
    "medium": 15,
    "high": 35,
    "critical": 60,
}


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------

def _lookup_risk_level(score: float) -> str:
    """将数值得分映射到风险等级。

    Args:
        score: 0-100 的分数

    Returns:
        'low' / 'medium' / 'high' / 'critical'
    """
    for threshold, level in _RISK_LEVEL_THRESHOLDS:
        if score >= threshold:
            return level
    return "low"


def _compute_dimension_weighted_score(
    dimension_scores: list[dict[str, Any]],
) -> tuple[float, dict[str, float]]:
    """按权重计算维度综合得分。

    Args:
        dimension_scores: 各维度评分 dict

    Returns:
        (综合得分, {维度名: 原始得分})
    """
    named_scores: dict[str, float] = {}

    for ds in dimension_scores:
        if hasattr(ds, "dimension"):
            dim = ds.dimension
            score = ds.score
        else:
            dim = ds.get("dimension", "unknown")
            score = ds.get("score", 50.0)
        named_scores[dim] = score

    total_weight = 0.0
    weighted_sum = 0.0

    for dim, weight in _DIMENSION_WEIGHTS.items():
        if dim in named_scores:
            weighted_sum += named_scores[dim] * weight
            total_weight += weight

    if total_weight <= 0:
        return 50.0, named_scores

    return weighted_sum / total_weight, named_scores


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

def calculate_risk_score(
    clause_reviews,
    dimension_scores: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """计算综合风险评分。

    Args:
        clause_reviews: 条款审查结果列表（ClauseReview 或 dict-like）
        dimension_scores: 可选的维度评分列表

    Returns:
        {
            "risk_score": float,
            "risk_level": str,
            "dimension_scores": dict,
            "critical_issues": list,
            "high_issues": list,
            "statistics": dict,
        }
    """
    # 维度加权得分
    if dimension_scores:
        dim_score, dim_named = _compute_dimension_weighted_score(dimension_scores)
    else:
        dim_score = 50.0
        dim_named = {}

    # 从条款中提取问题
    critical_issues: list[dict] = []
    high_issues: list[dict] = []
    clause_scores: dict[str, float] = {}
    total_severity_score = 0.0
    clause_count = 0

    for cr in clause_reviews:
        clause_count += 1

        # 兼容 Pydantic model 和 dict
        if hasattr(cr, "clause_id"):
            cid = cr.clause_id
            issues = cr.issues
            risk_score_val = cr.risk_score if hasattr(cr, "risk_score") else 0.0
        else:
            cid = cr.get("clause_id", "unknown")
            issues = cr.get("issues", [])
            risk_score_val = cr.get("risk_score", 0.0)

        clause_scores[cid] = risk_score_val
        total_severity_score += risk_score_val

        for issue in issues:
            issue_dict = {
                "keyword": issue.keyword if hasattr(issue, "keyword") else issue.get("keyword", ""),
                "severity": issue.severity if hasattr(issue, "severity") else issue.get("severity", "low"),
                "description": issue.description if hasattr(issue, "description") else issue.get("description", ""),
                "clause_id": cid,
            }
            severity = issue_dict["severity"]
            if severity == "critical":
                critical_issues.append(issue_dict)
            elif severity == "high":
                high_issues.append(issue_dict)

    # 条款风险分 + 维度风险分按比例混合
    clause_avg = (total_severity_score / clause_count) if clause_count > 0 else 0.0
    final_score = (dim_score * 0.6) + (clause_avg * 0.4)
    final_score = min(100.0, max(0.0, final_score))

    risk_level = _lookup_risk_level(final_score)

    issue_count = len(critical_issues) + len(high_issues)

    return {
        "risk_score": round(final_score, 2),
        "risk_level": risk_level,
        "dimension_scores": dim_named,
        "clause_scores": clause_scores,
        "critical_issues": critical_issues,
        "high_issues": high_issues,
        "statistics": {
            "clause_count": clause_count,
            "total_issues": issue_count,
            "critical_count": len(critical_issues),
            "high_count": len(high_issues),
            "dimension_score": round(dim_score, 2),
            "clause_avg_score": round(clause_avg, 2),
        },
    }


def generate_report(
    risk_data: dict[str, Any],
    *,
    review_id: str = "",
    contract_type: str = "",
) -> dict[str, Any]:
    """生成结构化的风险报告。

    Args:
        risk_data: calculate_risk_score 的返回值
        review_id: 审查记录 ID
        contract_type: 合同类型

    Returns:
        报告 dict，可直接存入 AIReview.summary
    """
    risk_level = risk_data.get("risk_level", "unknown")
    risk_score = risk_data.get("risk_score", 0.0)
    statistics = risk_data.get("statistics", {})

    # 行动建议
    recommendations: list[str] = []
    if risk_level == "critical":
        recommendations.append("【紧急】合同存在重大风险条款，建议暂停签署流程并立即启动法务审查")
        recommendations.append("重点处理以下关键问题：")
        for issue in risk_data.get("critical_issues", [])[:5]:
            recommendations.append(f"  - [{issue.get('clause_id', '?')}] {issue.get('description', '')}")
    elif risk_level == "high":
        recommendations.append("合同存在较多风险点，建议法务重点审查后签署")
        for issue in risk_data.get("high_issues", [])[:3]:
            recommendations.append(f"  - [{issue.get('clause_id', '?')}] {issue.get('description', '')}")
    elif risk_level == "medium":
        recommendations.append("合同存在部分风险，建议在签署前进行人工复核")
    else:
        recommendations.append("合同风险较低，可按正常流程推进")

    report: dict[str, Any] = {
        "review_id": review_id,
        "contract_type": contract_type,
        "risk_level": risk_level,
        "risk_score": risk_score,
        "recommendations": recommendations,
        "dimension_scores": risk_data.get("dimension_scores", {}),
        "statistics": statistics,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return report
