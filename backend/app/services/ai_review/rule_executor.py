# -*- coding: utf-8 -*-
"""可配置规则执行器（清单 detect_config + 硬规则表）。"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.services.ai_review.issue_schema import AiReviewIssue, normalize_dimension
from app.services.ai_review.config_store import get_hard_rules, get_review_checklists, get_risk_labels


def _label_for_gate(gate_id: str | None, label_map: dict[str, dict]) -> tuple[str | None, str | None]:
    if not gate_id:
        return None, None
    for lid, meta in label_map.items():
        if meta.get("gate_id") == gate_id:
            return lid, meta.get("name")
    return None, None


def evaluate_detect_config(text: str, config: dict[str, Any] | None) -> tuple[bool, str]:
    if not config:
        return False, ""
    dtype = config.get("type", "regex")
    if dtype == "regex":
        pattern = config.get("pattern", "")
        if pattern and re.search(pattern, text):
            return True, config.get("message", "规则命中")
    elif dtype == "amount_cn_missing":
        has_digit = bool(re.search(r"[￥¥]?\s*[\d,]+(?:\.\d+)?\s*元", text))
        has_cn = bool(re.search(r"[零壹贰叁肆伍陆柒捌玖拾佰仟万亿]+元", text))
        if has_digit and not has_cn:
            return True, config.get("message", "存在数字金额但未发现对应中文大写金额")
    elif dtype == "date_format_mixed":
        formats = []
        if re.search(r"\d{4}年\d{1,2}月\d{1,2}日", text):
            formats.append("cn")
        if re.search(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", text):
            formats.append("iso")
        if len(set(formats)) > 1:
            return True, config.get("message", "合同内日期格式不统一")
    elif dtype == "multi_newline":
        if re.search(r"\n{4,}", text):
            return True, config.get("message", "正文存在过多连续空行")
    return False, ""


def run_hard_rule(
    rule: dict[str, Any],
    text: str,
    *,
    amount: Optional[float] = None,
    counterparty_blacklisted: bool = False,
) -> AiReviewIssue | None:
    rule_type = rule.get("rule_type", "")
    cfg = rule.get("config") or {}
    if rule_type == "blacklist" and counterparty_blacklisted:
        triggered = True
        detail = "交易相对方处于黑名单状态"
    elif rule_type == "prepayment_ratio":
        match = re.search(cfg.get("pattern", r"预付款[^。\n]{0,40}?(\d{1,3})\s*%"), text)
        if not match:
            return None
        ratio = int(match.group(1))
        max_ratio = int(cfg.get("max_ratio", 30))
        if ratio <= max_ratio:
            return None
        triggered = True
        detail = f"预付款比例 {ratio}% 超过内部 {max_ratio}% 上限"
    elif rule_type == "amount_threshold":
        if amount is None:
            return None
        threshold = float(cfg.get("threshold", 1_000_000))
        if amount < threshold:
            return None
        triggered = True
        detail = f"合同金额 {amount:,.0f} 元达到阈值 {threshold:,.0f}"
    elif rule_type == "regex":
        pattern = cfg.get("pattern", "")
        if not pattern or not re.search(pattern, text, re.I if cfg.get("ignore_case") else 0):
            return None
        triggered = True
        detail = cfg.get("message", rule.get("title", "规则命中"))
    elif rule_type == "keyword_any":
        keywords = cfg.get("keywords") or []
        if not any(k in text for k in keywords):
            return None
        triggered = True
        detail = cfg.get("message", "命中关键词")
    elif rule_type == "missing_keywords":
        required = cfg.get("keywords") or []
        pattern = cfg.get("pattern") or "|".join(re.escape(k) for k in required)
        if not pattern or re.search(pattern, text):
            return None
        triggered = True
        detail = cfg.get("message", "缺少关键条款表述")
    elif rule_type == "sign_area_unclear":
        # 提及签字/盖章但未发现明确签署栏占位
        if not re.search(r"签字|盖章|签署", text):
            return None
        placeholder = cfg.get(
            "placeholder_pattern",
            r"(签字|盖章|签署).{0,20}(_{3,}|【|：|:|\s)",
        )
        if re.search(placeholder, text):
            return None
        triggered = True
        detail = cfg.get("message", "提及签字/盖章但未发现明确签署栏位")
    else:
        return None

    label_id = rule.get("label_id")
    label_map = {x["id"]: x for x in get_risk_labels().get("items", []) if "id" in x}
    label_name = label_map.get(label_id, {}).get("name") if label_id else None
    return AiReviewIssue(
        clause=rule.get("clause") or "合同条款",
        clause_ref=rule.get("clause") or "",
        dimension=normalize_dimension(rule.get("dimension")),
        label_id=label_id,
        label_name=label_name,
        gate_id=rule.get("gate_id"),
        risk_level=rule.get("risk_level", "medium"),
        confidence=float(cfg.get("confidence", 0.9)),
        title=rule.get("title") or rule.get("name", ""),
        description=detail,
        suggestion=rule.get("suggestion") or "",
        legal_basis=rule.get("legal_basis") or "",
        revision_method=rule.get("revision_method", "comment"),
        source="rule",
        rule_id=rule.get("rule_id"),
    )


def run_checklist_auto_detect(text: str) -> list[AiReviewIssue]:
    issues: list[AiReviewIssue] = []
    try:
        items = get_review_checklists().get("items", [])
    except Exception:
        return issues
    label_map = {x["id"]: x for x in get_risk_labels().get("items", []) if "id" in x}

    for item in items:
        if not item.get("auto_detectable") or item.get("enabled") is False:
            continue
        legacy_id = item.get("id")
        detect_cfg = item.get("detect_config")
        if isinstance(detect_cfg, str):
            try:
                detect_cfg = json.loads(detect_cfg)
            except json.JSONDecodeError:
                detect_cfg = None
        triggered, detail = evaluate_detect_config(text, detect_cfg)
        if not triggered:
            continue
        gate_id = item.get("gate_id") or "gate_consistency"
        label_id, label_name = _label_for_gate(gate_id, label_map)
        issues.append(
            AiReviewIssue(
                clause=item.get("item") or "形式审查",
                clause_ref=item.get("item") or "",
                dimension=normalize_dimension("compliance"),
                label_id=label_id,
                label_name=label_name,
                gate_id=gate_id,
                risk_level=item.get("risk_level") or "medium",
                confidence=0.92,
                title=item.get("item") or "",
                description=detail,
                suggestion=f"请核对：{item.get('description') or ''}",
                legal_basis="审查清单 auto_detectable",
                revision_method="comment",
                source="rule",
                rule_id=f"CK-{legacy_id}",
                checklist_item_id=int(legacy_id) if legacy_id is not None else None,
            )
        )
    return issues


def run_all_hard_rules(
    text: str,
    *,
    amount: Optional[float] = None,
    counterparty_blacklisted: bool = False,
) -> list[AiReviewIssue]:
    issues: list[AiReviewIssue] = []
    for rule in get_hard_rules():
        if not rule.get("enabled", True):
            continue
        issue = run_hard_rule(
            rule,
            text,
            amount=amount,
            counterparty_blacklisted=counterparty_blacklisted,
        )
        if issue:
            issues.append(issue)
    return issues
