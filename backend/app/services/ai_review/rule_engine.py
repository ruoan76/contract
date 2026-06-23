# -*- coding: utf-8 -*-
"""规则引擎 — 委托可配置 RuleExecutor。"""
from __future__ import annotations

from typing import Optional

from app.services.ai_review.issue_schema import AiReviewIssue
from app.services.ai_review.rule_executor import run_all_hard_rules, run_checklist_auto_detect


class RuleEngine:
    """合同硬规则 + checklist auto_detectable 项（读 ConfigStore）。"""

    def run(
        self,
        contract_text: str,
        *,
        contract_type: str = "other",
        amount: Optional[float] = None,
        counterparty_blacklisted: bool = False,
    ) -> list[AiReviewIssue]:
        text = (contract_text or "").strip()
        issues: list[AiReviewIssue] = []
        issues.extend(run_checklist_auto_detect(text))
        issues.extend(
            run_all_hard_rules(
                text,
                amount=amount,
                counterparty_blacklisted=counterparty_blacklisted,
            )
        )
        return issues


def run_rule_engine(
    contract_text: str,
    *,
    contract_type: str = "other",
    amount: Optional[float] = None,
    counterparty_blacklisted: bool = False,
) -> list[AiReviewIssue]:
    return RuleEngine().run(
        contract_text,
        contract_type=contract_type,
        amount=amount,
        counterparty_blacklisted=counterparty_blacklisted,
    )
