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
        counterparty_blacklisted: bool = False,
    ) -> list[AiReviewIssue]:
        text = (contract_text or "").strip()
        issues: list[AiReviewIssue] = []
        issues.extend(self._check_prepayment(text))
        issues.extend(self._check_auto_detectable(text))
        issues.extend(self._check_amount_threshold(amount))
        issues.extend(self._check_batch1_rules(text))
        issues.extend(self._check_redline_keywords(text))
        issues.extend(self._check_missing_clauses(text))
        if counterparty_blacklisted:
            issues.extend(self._check_blacklist())
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


    def _check_batch1_rules(self, text: str) -> list[AiReviewIssue]:
        """Batch-1：金额/日期/格式 + 关键词红线。"""
        issues: list[AiReviewIssue] = []

        if re.search(r"[￥¥]\s*[\d,]+", text) and re.search(r"USD|EUR|\$|美元|欧元", text, re.I):
            issues.append(
                AiReviewIssue(
                    clause="价款条款",
                    dimension="finance_check",
                    label_id="L06",
                    gate_id="gate_consistency",
                    risk_level="medium",
                    confidence=0.9,
                    title="币种混用",
                    description="合同内同时出现人民币与外币表述，存在币种混用风险",
                    suggestion="建议统一币种并明确汇率与结算方式",
                    legal_basis="审查清单",
                    source="rule",
                    rule_id="CK-46",
                    revision_method="comment",
                )
            )

        if re.search(r"单方.{0,6}(解除|终止|撤销)", text):
            issues.append(
                AiReviewIssue(
                    clause="解除条款",
                    dimension="risk_assessment",
                    label_id="L08",
                    gate_id="gate_clause",
                    risk_level="high",
                    confidence=0.88,
                    title="单方解除权",
                    description="存在单方解除/终止表述，可能对我方不利",
                    suggestion="建议改为双方协商或限定法定解除条件",
                    legal_basis="民法典合同编",
                    source="rule",
                    rule_id="CK-47",
                )
            )

        if re.search(r"放弃.{0,4}诉权|无限.{0,4}责任", text):
            issues.append(
                AiReviewIssue(
                    clause="责任条款",
                    dimension="risk_assessment",
                    label_id="L08",
                    gate_id="gate_clause",
                    risk_level="critical",
                    confidence=0.92,
                    title="责任限制异常",
                    description="存在放弃诉权或无限责任表述",
                    suggestion="建议删除或限缩责任范围",
                    legal_basis="民法典",
                    source="rule",
                    rule_id="CK-48",
                )
            )

        if not re.search(r"争议|仲裁|管辖|诉讼", text):
            issues.append(
                AiReviewIssue(
                    clause="争议解决",
                    dimension="risk_assessment",
                    label_id="L11",
                    gate_id="gate_clause",
                    risk_level="high",
                    confidence=0.85,
                    title="争议解决条款缺失",
                    description="未发现争议解决/管辖/仲裁条款",
                    suggestion="建议补充争议解决方式与管辖约定",
                    legal_basis="审查清单",
                    source="rule",
                    rule_id="CK-50",
                )
            )

        if "签字" in text or "盖章" in text:
            if not re.search(r"(签字|盖章|签署).{0,20}(_{3,}|【|：|:|\s)", text):
                issues.append(
                        AiReviewIssue(
                            clause="签署页",
                            dimension="compliance_check",
                            label_id="L03",
                            gate_id="gate_consistency",
                            risk_level="medium",
                            confidence=0.75,
                            title="签署栏不明确",
                            description="提及签字/盖章但未发现明确签署栏位",
                            suggestion="建议补充签署页与授权信息",
                            source="rule",
                            rule_id="CK-49",
                        )
                    )

        return issues



    def _check_redline_keywords(self, text: str) -> list[AiReviewIssue]:
        """检测极端/异常表述（霸权条款）。"""
        issues: list[AiReviewIssue] = []
        dangerous = [
            (r"概不负责", "霸王免责", "L01", "gate_validity", "存在概不负责等无效免责表述", "high"),
            (r"一切.{0,6}后果", "兜底责任", "L08", "gate_clause", "兜底责任表述", "medium"),
            (r"最终解释权", "霸王条款", "L01", "gate_validity", "涉嫌无效格式条款", "high"),
        ]
        for pattern, title, lid, gate, desc, rl in dangerous:
            if re.search(pattern, text):
                issues.append(
                    AiReviewIssue(
                        clause='责任/效力条款', clause_ref='全文', dimension='risk_assessment',
                        label_id=lid, label_name='', gate_id=gate, risk_level=rl, confidence=0.9,
                        title=title, description=desc, suggestion='建议删除或按照民法典规范表述',
                        legal_basis='民法典第497条', revision_method='delete', source='rule', rule_id=f'RL-{lid}',
                    )
                )
        return issues

    def _check_missing_clauses(self, text: str) -> list[AiReviewIssue]:
        """检测关键法律条款的缺失。"""
        issues: list[AiReviewIssue] = []
        if not re.search(r'知识产权\|专利\|著作权\|软件许可', text):
            issues.append(
                AiReviewIssue(clause='知识产权', dimension='risk_assessment', label_id='L12',
                    gate_id='gate_clause', risk_level='medium', confidence=0.85,
                    title='知识产权归属缺失', description='未发现知识产权/专利/著作权归属条款',
                    suggestion='建议补充知识产权归属条款', legal_basis='民法典第847条',
                    source='rule', rule_id='CK-52', revision_method='add_clause'))
        if not re.search(r'保密\|商业秘密\|不得泄露', text):
            issues.append(
                AiReviewIssue(clause='保密', dimension='risk_assessment', label_id='L12',
                    gate_id='gate_clause', risk_level='medium', confidence=0.8,
                    title='保密条款缺失', description='未发现保密义务相关约定',
                    suggestion='建议补充保密条款及违约责任', legal_basis='反不正当竞争法第9条',
                    source='rule', rule_id='CK-53', revision_method='add_clause'))
        return issues

    def _check_blacklist(self) -> list[AiReviewIssue]:
        return [
            AiReviewIssue(
                clause="相对方",
                dimension="compliance_check",
                label_id="L03",
                gate_id="gate_subject",
                risk_level="critical",
                confidence=0.99,
                title="相对方黑名单",
                description="交易相对方处于黑名单状态",
                suggestion="禁止与该相对方签约，须升级审批",
                legal_basis="集团相对方管理制度",
                source="rule",
                rule_id="TH-BLACKLIST",
            )
        ]


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
