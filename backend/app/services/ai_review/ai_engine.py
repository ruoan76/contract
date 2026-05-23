# -*- coding: utf-8 -*-
"""AI 审查引擎 — 核心审查逻辑 via Qwen3.6"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import openai
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.ai_review.clause_parser import Clause
from app.services.ai_review.risk_scorer import calculate_risk_score, RiskScore
from app.services.ai_review.seed_store import (
    get_risk_labels,
    get_review_checklists,
    get_contract_type_map,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 模块常量 — Prompt 模板
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """你是一位资深合同审查专家，负责对企业合同进行全方位 AI 审查。
审查需覆盖合规性、风险条款、财务条款、履约能力和异常检测五个维度。
请以 JSON 格式输出审查结果，严格遵守提供的 schema 要求。"""

DIMENSION_PROMPTS: dict[str, str] = {
    "compliance": """审查合同的合规性：
1. 合同主体是否合法有效
2. 是否存在违反法律法规的条款
3. 格式条款是否符合《民法典》要求
4. 是否缺少法定必备条款

请输出 JSON：
{
  "dimension": "compliance",
  "score": 0-100,
  "issues": [{"keyword": str, "severity": "low|medium|high|critical", "description": str}],
  "summary": str
}""",

    "risk": """审查合同的风险条款：
1. 违约责任是否明确合理
2. 赔偿上限是否过低
3. 争议解决条款是否对我方有利
4. 保密条款的覆盖范围

请输出 JSON：
{
  "dimension": "risk",
  "score": 0-100,
  "issues": [{"keyword": str, "severity": "low|medium|high|critical", "description": str}],
  "summary": str
}""",

    "financial": """审查合同的财务条款：
1. 价款金额是否明确
2. 付款条件是否合理
3. 发票、税费条款是否完备
4. 保证金/定金条款是否适当

请输出 JSON：
{
  "dimension": "financial",
  "score": 0-100,
  "issues": [{"keyword": str, "severity": "low|medium|high|critical", "description": str}],
  "summary": str
}""",

    "capability": """审查合同的履约能力：
1. 交付周期是否合理
2. 质量标准是否明确可执行
3. 验收条件是否清晰
4. 单方义务是否过重

请输出 JSON：
{
  "dimension": "capability",
  "score": 0-100,
  "issues": [{"keyword": str, "severity": "low|medium|high|critical", "description": str}],
  "summary": str
}""",

    "anomaly": """审查合同的异常条款：
1. 是否存在非常规或不合理的条款
2. 条款之间是否存在矛盾
3. 是否存在隐藏风险
4. 用词是否精准无歧义

请输出 JSON：
{
  "dimension": "anomaly",
  "score": 0-100,
  "issues": [{"keyword": str, "severity": "low|medium|high|critical", "description": str}],
  "summary": str
}""",
}

DIMENSION_LABELS = {
    "compliance": "合规性审查",
    "risk": "风险条款审查",
    "financial": "财务条款审查",
    "capability": "履约能力评估",
    "anomaly": "异常检测",
}


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class Issue(BaseModel):
    """审查发现的问题"""

    keyword: str = Field(description="问题关键词")
    severity: str = Field(description="严重程度: low/medium/high/critical")
    description: str = Field(description="问题描述")


class DimensionScore(BaseModel):
    """单个维度的审查结果"""

    dimension: str = Field(description="维度名称")
    score: float = Field(description="得分 0-100")
    issues: List[Issue] = Field(default_factory=list, description="问题列表")
    summary: str = Field(default="", description="维度摘要")


class DimensionRequest(BaseModel):
    """维度审查请求"""

    contract_text: str = Field(description="合同全文")
    clauses: List[Clause] = Field(default_factory=list, description="条款列表")
    contract_type: str = Field(default="other", description="合同类型")
    dimension: str = Field(description="审查维度")
    checklist: List[dict] = Field(default_factory=list, description="审查清单")
    risk_labels: List[dict] = Field(default_factory=list, description="风险标签")


class ReviewContext(BaseModel):
    """审查上下文"""

    contract_text: str = Field(default="", description="合同全文")
    clauses: List[Clause] = Field(default_factory=list, description="条款列表")
    contract_type: str = Field(default="other", description="合同类型")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")


class ClauseReview(BaseModel):
    """单一条款的审查结果"""

    clause_id: str = Field(default="", description="条款 ID")
    title: str = Field(default="", description="条款标题")
    section_type: str = Field(default="other", description="条款类型")
    risk_level: str = Field(default="low", description="风险等级: low/medium/high/critical")
    risk_score: float = Field(default=0.0, description="风险评分 0-100")
    issues: List[Issue] = Field(default_factory=list, description="问题列表")
    suggestions: List[str] = Field(default_factory=list, description="修改建议")


class ReviewResult(BaseModel):
    """审查结果"""

    overall_risk_level: str = Field(default="low", description="整体风险等级")
    overall_risk_score: float = Field(default=0.0, description="整体风险评分 0-100")
    recommendation: str = Field(default="", description="总体审查建议")
    clause_reviews: List[ClauseReview] = Field(default_factory=list, description="条款审查结果")
    dimension_scores: List[DimensionScore] = Field(default_factory=list, description="五维评分")
    summary: Dict[str, Any] = Field(default_factory=dict, description="摘要信息")


# ---------------------------------------------------------------------------
# AIReviewEngine
# ---------------------------------------------------------------------------

class AIReviewEngine:
    """AI 合同审查引擎"""

    def __init__(self) -> None:
        self._client = openai.AsyncOpenAI(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
        )
        self._model = settings.AI_MODEL
        self._temperature = settings.AI_TEMPERATURE
        self._max_tokens = settings.AI_MAX_TOKENS

    async def review(
        self,
        full_text: str,
        clauses: List[Clause],
        contract_type: str = "other",
    ) -> ReviewResult:
        """执行多维度合同审查。

        Args:
            full_text: 合同全文
            clauses: 已切分的条款列表
            contract_type: 合同类型

        Returns:
            ReviewResult 包含全部审查结果
        """
        contract_type = self._resolve_contract_type(contract_type)

        # 加载种子数据
        risk_labels = self._safe_load(get_risk_labels, fallback={"items": []})
        checklists = self._safe_load(get_review_checklists, fallback={"items": []})

        # 并行执行五维审查
        dimension_tasks = [
            self._review_one_dimension(DimensionRequest(
                contract_text=full_text,
                clauses=clauses,
                contract_type=contract_type,
                dimension=dim,
                checklist=checklists.get("items", []),
                risk_labels=risk_labels.get("items", []),
            ))
            for dim in DIMENSION_PROMPTS
        ]

        dimension_results: List[DimensionScore] = []
        gathered = await asyncio.gather(*dimension_tasks, return_exceptions=True)

        for result in gathered:
            if isinstance(result, Exception):
                logger.warning("维度审查异常: %s", result)
                dimension_results.append(
                    DimensionScore(dimension="unknown", score=50.0, issues=[], summary="审查失败")
                )
            else:
                dimension_results.append(result)

        # 汇总条款级审查结果
        clause_reviews = self._generate_clause_reviews(clauses, dimension_results)

        # 计算综合风险分
        risk_data = calculate_risk_score(clause_reviews, dimension_results)

        # 生成总体建议
        recommendation = self._build_recommendation(dimension_results, risk_data)

        return ReviewResult(
            overall_risk_level=risk_data["risk_level"],
            overall_risk_score=risk_data["risk_score"],
            recommendation=recommendation,
            clause_reviews=clause_reviews,
            dimension_scores=dimension_results,
            summary={
                "dimension_count": len(dimension_results),
                "clause_count": len(clause_reviews),
                "issue_count": sum(len(d.issues) for d in dimension_results),
                "contract_type": contract_type,
                "model_version": self._model,
            },
        )

    async def _review_one_dimension(
        self, request: DimensionRequest,
    ) -> DimensionScore:
        """执行单个维度的 LLM 审查。

        Args:
            request: 维度审查请求

        Returns:
            DimensionScore 结果
        """
        prompt = self._build_dimension_prompt(request)

        try:
            llm_result = await self._call_llm(prompt)
            return DimensionScore.model_validate(llm_result)
        except openai.APITimeoutError as e:
            logger.error("LLM 超时 (%s): %s", request.dimension, e)
            return DimensionScore(
                dimension=request.dimension,
                score=50.0,
                summary="LLM 调用超时，请使用人工审查",
            )
        except openai.APIStatusError as e:
            logger.error("LLM 状态错误 (%s): %s", request.dimension, e)
            return DimensionScore(
                dimension=request.dimension,
                score=50.0,
                summary="LLM 服务不可用，请使用人工审查",
            )
        except Exception as e:
            logger.error("LLM 审查失败 (%s): %s", request.dimension, e)
            return DimensionScore(
                dimension=request.dimension,
                score=50.0,
                summary="审查过程中发生错误，请使用人工审查",
            )

    def _build_dimension_prompt(self, request: DimensionRequest) -> str:
        """构建单个维度审查的 prompt。

        Args:
            request: 维度审查请求

        Returns:
            完整 prompt 字符串
        """
        # 提取与维度相关的条款
        relevant_clauses = self._filter_relevant_clauses(
            request.clauses, request.dimension
        )

        clauses_text = ""
        for c in relevant_clauses[:10]:  # 限制最多 10 条，避免上下文过长
            clauses_text += f"\n[条款 {c.clause_id}] {c.title}\n{c.content[:500]}\n"

        checklist_text = ""
        for item in request.checklist[:10]:
            checklist_text += f"- {item.get('item', '')}: {item.get('description', '')}\n"

        return (
            f"{_SYSTEM_PROMPT}\n\n"
            f"{DIMENSION_PROMPTS[request.dimension]}\n\n"
            f"合同类型: {request.contract_type}\n\n"
            f"合同全文:\n{request.contract_text[:8000]}\n\n"
            f"重点条款:\n{clauses_text}\n\n"
            f"审查清单:\n{checklist_text}\n\n"
            f"请直接输出 JSON，不要包含 markdown 标记或其他格式。"
        )

    def _filter_relevant_clauses(
        self,
        clauses: List[Clause],
        dimension: str,
    ) -> List[Clause]:
        """筛选与给定维度相关的条款。"""
        type_map = {
            "compliance": ["definitions", "rights_obligations", "other"],
            "risk": ["breach", "dispute", "termination", "force_majeure"],
            "financial": ["financial", "breach"],
            "capability": ["rights_obligations", "financial", "termination"],
            "anomaly": [],  # 审查全部
        }
        target_types = type_map.get(dimension, [])
        if not target_types:
            return clauses
        return [c for c in clauses if c.section_type in target_types]

    async def _call_llm(self, prompt: str) -> dict:
        """调用 LLM 获取审查结果。

        Args:
            prompt: 提示词

        Returns:
            LLM 输出的 JSON dict

        Raises:
            ValueError: JSON 解析失败
        """
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            response_format={"type": "json_object"},
        )

        raw_text = response.choices[0].message.content or "{}"

        # 处理可能的 markdown 代码块
        if raw_text.startswith("```"):
            # 移除 ```json 和 ``` 标记
            lines = raw_text.strip().split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw_text = "\n".join(lines)

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error("LLM JSON 解析失败: %s", e)
            raise ValueError(f"LLM 输出非合法 JSON: {raw_text[:200]}") from e

    def _generate_clause_reviews(
        self,
        clauses: List[Clause],
        dimension_results: list[DimensionScore],
    ) -> List[ClauseReview]:
        """根据维度审查结果生成条款级审查结果。

        策略：将各维度的问题映射到对应条款上。

        Args:
            clauses: 条款列表
            dimension_results: 维度评分结果

        Returns:
            条款审查结果列表
        """
        clause_reviews: list[ClauseReview] = []

        for clause in clauses:
            # 收集与该条款相关的问题
            clause_issues: list[Issue] = []
            all_suggestions: list[str] = []

            for dim_result in dimension_results:
                for issue in dim_result.issues:
                    if any(kw in clause.content or kw in clause.title for kw in [issue.keyword]):
                        clause_issues.append(issue)

            # 基于风险关键词补充问题
            for kw in clause.risk_keywords:
                if not any(i.keyword == kw for i in clause_issues):
                    clause_issues.append(
                        Issue(keyword=kw, severity="medium", description=f"条款包含风险关键词: {kw}")
                    )

            # 生成建议
            clause_score = self._compute_clause_risk_score(clause_issues)
            if clause_score > 50:
                all_suggestions.append(
                    f"本条款（{clause.title}）风险较高，建议法务重点审查"
                )
            for issue in clause_issues:
                if issue.severity in ("high", "critical"):
                    all_suggestions.append(f"建议修改: {issue.description}")

            # 风险等级映射
            max_severity = "low"
            severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            for issue in clause_issues:
                if severity_order.get(issue.severity, 0) > severity_order.get(max_severity, 0):
                    max_severity = issue.severity

            clause_reviews.append(
                ClauseReview(
                    clause_id=clause.clause_id,
                    title=clause.title,
                    section_type=clause.section_type,
                    risk_level=max_severity,
                    risk_score=self._compute_clause_risk_score(clause_issues),
                    issues=clause_issues,
                    suggestions=all_suggestions,
                )
            )

        return clause_reviews

    @staticmethod
    def _compute_clause_risk_score(issues: List[Issue]) -> float:
        """计算单一条款的风险得分。"""
        if not issues:
            return 0.0
        severity_scores = {"low": 10, "medium": 30, "high": 60, "critical": 90}
        return float(max(severity_scores.get(i.severity, 0) for i in issues))

    def _build_recommendation(
        self,
        dimension_results: List[DimensionScore],
        risk_data: Dict[str, Any],
    ) -> str:
        """生成总体审查建议。

        Args:
            dimension_results: 维度评分
            risk_data: 风险数据

        Returns:
            建议文本
        """
        risk_level = risk_data.get("risk_level", "unknown")
        risk_score = risk_data.get("risk_score", 0)

        parts: list[str] = []
        parts.append(f"综合风险评分: {risk_score:.1f}，等级: {risk_level}")
        parts.append("")

        for dim in dimension_results:
            if dim.score < 50:
                parts.append(f"【{DIMENSION_LABELS.get(dim.dimension, dim.dimension)}】得分 {dim.score:.1f}，需重点关注：{dim.summary}")

        if not parts[2:]:
            parts.append("各维度审查均未发现重大问题。建议在签署前进行最终人工复核。")

        return "\n".join(parts)

    def _resolve_contract_type(self, contract_type: str) -> str:
        """将外部合同类型映射为 AI profile key。

        Args:
            contract_type: 原始合同类型

        Returns:
            AI profile key
        """
        try:
            type_map = get_contract_type_map()
            for mapping in type_map.get("platform_mapping", []):
                if mapping.get("contract_type") == contract_type:
                    return mapping.get("ai_profile_key", "服务合同")
        except Exception as e:
            logger.warning("加载合同类型映射失败: %s", e)
        return contract_type or "other"

    @staticmethod
    def _safe_load(loader, fallback: dict) -> dict:
        """安全加载种子数据，失败时回退到默认值。"""
        try:
            return loader()
        except Exception as e:
            logger.warning("种子数据加载失败: %s", e)
            return fallback


# ---------------------------------------------------------------------------
# 便捷函数入口
# ---------------------------------------------------------------------------

_engine: Optional[AIReviewEngine] = None


def get_engine() -> AIReviewEngine:
    """获取审查引擎单例。"""
    global _engine
    if _engine is None:
        _engine = AIReviewEngine()
    return _engine


async def review_contract(
    contract_text: str,
    clauses: List[Clause],
    contract_type: str = "other",
) -> ReviewResult:
    """合同审查快捷函数。

    Args:
        contract_text: 合同全文
        clauses: 条款列表
        contract_type: 合同类型

    Returns:
        ReviewResult 审查结果
    """
    engine = get_engine()
    return await engine.review(contract_text, clauses, contract_type)
