# -*- coding: utf-8 -*-
"""规则引擎 — 可验证条款检测（与 LLM 分工）。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from app.services.ai_review.issue_schema import AiReviewIssue, normalize_dimension
from app.services.ai_review.seed_store import get_review_checklists, get_risk_labels

THRESHOLDS_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "thresholds.json"
)


def _load_thresholds() -> dict[str, Any]:
    try:
        return json.loads(THRESHOLDS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"simple_max": 100_000, "standard_max": 1_000_000}


class RuleEngine:
    """合同硬规则 + checklist auto_detectable 项。"""

    def run(
        self,
        contract_text: str,
        *,
        contract_type: str = "other",
        amount: Optional[float] = None,
    ) -> list[AiReviewIssue]:
        text = (contract_text or "").strip()
        issues: list[AiReviewIssue] = []
        issues.extend(self._check_prepayment(text))
        issues.extend(self._check_auto_detectable(text))
        issues.extend(self._check_amount_threshold(amount))
        return issues

    def _check_prepayment(self, text: str) -> list[AiReviewIssue]:
        issues: list[AiReviewIssue] = []
        match = re.search(r"预付款[^。\n]{0,40}?(\d{1,3})\s*%", text)
        if not match:
            return issues
        ratio = int(match.group(1))
        if ratio <= 30:
            return issues
        issues.append(
            AiReviewIssue(
                clause="付款条款",
                clause_ref="付款条款",
                dimension="finance_check",
                label_id="L06",
                label_name="价款与支付",
                gate_id="gate_clause",
                risk_level="medium" if ratio <= 40 else "high",
                confidence=0.95,
                title="采购预付款上限",
                description=f"预付款比例 {ratio}% 超过内部 30% 上限",
                suggestion="建议将预付款比例控制在 30% 以内",
                legal_basis="内部财务制度",
                revision_method="comment",
                source="rule",
                rule_id="PR-001",
                exposure_summary=f"预付款 {ratio}%",
            )
        )
        return issues

    def _check_auto_detectable(self, text: str) -> list[AiReviewIssue]:
        """checklist 中 auto_detectable=true 的项。"""
        issues: list[AiReviewIssue] = []
        try:
            checklists = get_review_checklists().get("items", [])
        except Exception:
            return issues

        label_map = {x["id"]: x for x in get_risk_labels().get("items", []) if "id" in x}

        for item in checklists:
            if not item.get("auto_detectable"):
                continue
            item_id = item.get("id")
            desc = item.get("description") or item.get("item") or ""
            gate_id = item.get("gate_id") or "gate_consistency"
            risk_level = item.get("risk_level") or "medium"

            triggered = False
            detail = desc

            if item_id == 44:
                # 金额大小写一致 — 简化为检测是否同时出现数字金额与中文大写
                has_digit_amount = bool(re.search(r"[￥¥]?\s*[\d,]+(?:\.\d+)?\s*元", text))
                has_cn_amount = bool(re.search(r"[零壹贰叁肆伍陆柒捌玖拾佰仟万亿]+元", text))
                if has_digit_amount and not has_cn_amount:
                    triggered = True
                    detail = "存在数字金额但未发现对应中文大写金额"
            elif item_id == 45:
                # 日期格式 — 检测多种格式混用
                formats = []
                if re.search(r"\d{4}年\d{1,2}月\d{1,2}日", text):
                    formats.append("cn")
                if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", text):
                    formats.append("iso")
                if len(set(formats)) > 1:
                    triggered = True
                    detail = "合同内日期格式不统一"
            elif item_id == 51:
                # 格式规范 — 连续空行过多
                if re.search(r"\n{4,}", text):
                    triggered = True
                    detail = "正文存在过多连续空行，排版待规范"

            if not triggered:
                continue

            label_id = None
            label_name = None
            for lid, meta in label_map.items():
                if meta.get("gate_id") == gate_id:
                    label_id = lid
                    label_name = meta.get("name")
                    break

            issues.append(
                AiReviewIssue(
                    clause=item.get("item") or "形式审查",
                    clause_ref=item.get("item") or "",
                    dimension=normalize_dimension("compliance"),
                    label_id=label_id,
                    label_name=label_name,
                    gate_id=gate_id,
                    risk_level=risk_level,
                    confidence=0.92,
                    title=item.get("item") or "",
                    description=detail,
                    suggestion=f"请核对：{desc}",
                    legal_basis="审查清单 auto_detectable",
                    revision_method="comment",
                    source="rule",
                    rule_id=f"CK-{item_id}",
                )
            )
        return issues

    def _check_amount_threshold(self, amount: Optional[float]) -> list[AiReviewIssue]:
        if amount is None:
            return []
        thresholds = _load_thresholds()
        board = float(thresholds.get("board_threshold") or 1_000_000)
        if amount < board:
            return []
        return [
            AiReviewIssue(
                clause="合同金额",
                dimension="finance_check",
                label_id="L06",
                gate_id="gate_clause",
                risk_level="medium",
                confidence=0.99,
                title="大额合同",
                description=f"合同金额 {amount:,.0f} 元达到大额/董事会审批阈值",
                suggestion="请确认审批流程含高管/董事会节点",
                legal_basis="集团审批阈值配置",
                source="rule",
                rule_id="TH-BOARD",
            )
        ]


def run_rule_engine(
    contract_text: str,
    *,
    contract_type: str = "other",
    amount: Optional[float] = None,
) -> list[AiReviewIssue]:
    return RuleEngine().run(contract_text, contract_type=contract_type, amount=amount)
