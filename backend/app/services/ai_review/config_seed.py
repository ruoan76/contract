# -*- coding: utf-8 -*-
"""从 JSON 种子幂等导入 AI 审查配置到数据库。"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select, update

from app.db.database import async_session
from app.models.ai_review_config import (
    AIConfigVersion,
    AIHardRule,
    AILegalSnippet,
    AIReviewChecklistItem,
    AIRevisionRoutingRule,
    AIRiskLabel,
)
from app.services.ai_review.config_store import refresh_config_cache

BACKEND = Path(__file__).resolve().parents[3]
GENERATED = BACKEND / "seeds" / "ai_review" / "generated"
LEGAL_PATH = BACKEND / "seeds" / "ai_review" / "legal_snippets.json"

DETECT_PRESETS: dict[int, dict] = {
    44: {"type": "amount_cn_missing", "message": "存在数字金额但未发现对应中文大写金额"},
    45: {"type": "date_format_mixed", "message": "合同内日期格式不统一"},
    51: {"type": "multi_newline", "message": "正文存在过多连续空行，排版待规范"},
}

DEFAULT_HARD_RULES: list[dict] = [
    {
        "rule_id": "PR-001",
        "name": "采购预付款上限",
        "rule_type": "prepayment_ratio",
        "config_json": {"pattern": r"预付款[^。\n]{0,40}?(\d{1,3})\s*%", "max_ratio": 30},
        "risk_level": "high",
        "label_id": "L06",
        "gate_id": "gate_clause",
        "dimension": "finance_check",
        "title": "采购预付款上限",
        "suggestion": "建议将预付款比例控制在 30% 以内",
        "legal_basis": "内部财务制度",
        "revision_method": "comment",
        "clause": "付款条款",
    },
    {
        "rule_id": "CK-46",
        "name": "币种混用",
        "rule_type": "regex",
        "config_json": {
            "pattern": r"[￥¥]\s*[\d,]+.*(?:USD|EUR|\$|美元|欧元)",
            "message": "合同内同时出现人民币与外币表述",
            "ignore_case": True,
        },
        "risk_level": "medium",
        "label_id": "L06",
        "gate_id": "gate_consistency",
        "dimension": "finance_check",
        "title": "币种混用",
        "suggestion": "建议统一币种并明确汇率与结算方式",
        "legal_basis": "审查清单",
        "clause": "价款条款",
    },
    {
        "rule_id": "CK-47",
        "name": "单方解除权",
        "rule_type": "regex",
        "config_json": {"pattern": r"单方.{0,6}(解除|终止|撤销)", "message": "存在单方解除/终止表述"},
        "risk_level": "high",
        "label_id": "L08",
        "gate_id": "gate_clause",
        "dimension": "risk_assessment",
        "title": "单方解除权",
        "suggestion": "建议改为双方协商或限定法定解除条件",
        "legal_basis": "民法典合同编",
        "clause": "解除条款",
    },
    {
        "rule_id": "CK-48",
        "name": "责任限制异常",
        "rule_type": "regex",
        "config_json": {"pattern": r"放弃.{0,4}诉权|无限.{0,4}责任", "message": "存在放弃诉权或无限责任表述"},
        "risk_level": "critical",
        "label_id": "L08",
        "gate_id": "gate_clause",
        "dimension": "risk_assessment",
        "title": "责任限制异常",
        "suggestion": "建议删除或限缩责任范围",
        "legal_basis": "民法典",
        "clause": "责任条款",
    },
    {
        "rule_id": "CK-49",
        "name": "签署栏不明确",
        "rule_type": "sign_area_unclear",
        "config_json": {
            "placeholder_pattern": r"(签字|盖章|签署).{0,20}(_{3,}|【|：|:|\s)",
            "message": "提及签字/盖章但未发现明确签署栏位",
        },
        "risk_level": "medium",
        "label_id": "L03",
        "gate_id": "gate_consistency",
        "dimension": "compliance_check",
        "title": "签署栏不明确",
        "suggestion": "建议补充签署页与授权信息",
        "clause": "签署页",
    },
    {
        "rule_id": "CK-50",
        "name": "争议解决条款缺失",
        "rule_type": "missing_keywords",
        "config_json": {"keywords": ["争议", "仲裁", "管辖", "诉讼"], "message": "未发现争议解决/管辖/仲裁条款"},
        "risk_level": "high",
        "label_id": "L11",
        "gate_id": "gate_clause",
        "dimension": "risk_assessment",
        "title": "争议解决条款缺失",
        "suggestion": "建议补充争议解决方式与管辖约定",
        "legal_basis": "审查清单",
        "clause": "争议解决",
    },
    {
        "rule_id": "CK-52",
        "name": "知识产权归属缺失",
        "rule_type": "missing_keywords",
        "config_json": {
            "pattern": r"知识产权|专利|著作权|软件许可",
            "message": "未发现知识产权/专利/著作权归属条款",
        },
        "risk_level": "medium",
        "label_id": "L12",
        "gate_id": "gate_clause",
        "dimension": "risk_assessment",
        "title": "知识产权归属缺失",
        "suggestion": "建议补充知识产权归属条款",
        "legal_basis": "民法典第847条",
        "revision_method": "add_clause",
        "clause": "知识产权",
    },
    {
        "rule_id": "CK-53",
        "name": "保密条款缺失",
        "rule_type": "missing_keywords",
        "config_json": {
            "pattern": r"保密|商业秘密|不得泄露",
            "message": "未发现保密义务相关约定",
        },
        "risk_level": "medium",
        "label_id": "L12",
        "gate_id": "gate_clause",
        "dimension": "risk_assessment",
        "title": "保密条款缺失",
        "suggestion": "建议补充保密条款及违约责任",
        "legal_basis": "反不正当竞争法第9条",
        "revision_method": "add_clause",
        "clause": "保密",
    },
    {
        "rule_id": "TH-BOARD",
        "name": "大额合同",
        "rule_type": "amount_threshold",
        "config_json": {"threshold": 1000000},
        "risk_level": "medium",
        "label_id": "L06",
        "gate_id": "gate_clause",
        "dimension": "finance_check",
        "title": "大额合同",
        "suggestion": "请确认审批流程含高管/董事会节点",
        "legal_basis": "集团审批阈值配置",
        "clause": "合同金额",
    },
    {
        "rule_id": "TH-BLACKLIST",
        "name": "相对方黑名单",
        "rule_type": "blacklist",
        "config_json": {},
        "risk_level": "critical",
        "label_id": "L03",
        "gate_id": "gate_subject",
        "dimension": "compliance_check",
        "title": "相对方黑名单",
        "suggestion": "禁止与该相对方签约，须升级审批",
        "legal_basis": "集团相对方管理制度",
        "clause": "相对方",
    },
    {
        "rule_id": "RL-L01",
        "name": "霸王免责",
        "rule_type": "regex",
        "config_json": {"pattern": r"概不负责", "message": "存在概不负责等无效免责表述"},
        "risk_level": "high",
        "label_id": "L01",
        "gate_id": "gate_validity",
        "dimension": "risk_assessment",
        "title": "霸王免责",
        "suggestion": "建议删除或按照民法典规范表述",
        "legal_basis": "民法典第497条",
        "revision_method": "delete",
        "clause": "责任/效力条款",
    },
    {
        "rule_id": "RL-L08-1",
        "name": "兜底责任",
        "rule_type": "regex",
        "config_json": {"pattern": r"一切.{0,6}后果", "message": "兜底责任表述"},
        "risk_level": "medium",
        "label_id": "L08",
        "gate_id": "gate_clause",
        "dimension": "risk_assessment",
        "title": "兜底责任",
        "suggestion": "建议删除或限缩责任范围",
        "legal_basis": "民法典",
        "revision_method": "delete",
        "clause": "责任/效力条款",
    },
    {
        "rule_id": "RL-L01-2",
        "name": "霸王条款",
        "rule_type": "regex",
        "config_json": {"pattern": r"最终解释权", "message": "涉嫌无效格式条款"},
        "risk_level": "high",
        "label_id": "L01",
        "gate_id": "gate_validity",
        "dimension": "risk_assessment",
        "title": "霸王条款",
        "suggestion": "建议删除或按照民法典规范表述",
        "legal_basis": "民法典第497条",
        "revision_method": "delete",
        "clause": "责任/效力条款",
    },
]


async def import_from_json_seeds(version: str, *, published_by: int | None = None) -> str:
    """幂等导入 JSON 种子并刷新 ConfigStore 缓存。"""
    async with async_session() as db:
        await db.execute(update(AIConfigVersion).values(is_current=False))
        db.add(
            AIConfigVersion(
                version=version,
                is_current=True,
                published_by=published_by,
                note="种子导入",
            )
        )

        checklists = json.loads((GENERATED / "review_checklists.json").read_text(encoding="utf-8"))
        for item in checklists.get("items", []):
            lid = item.get("id")
            detect = DETECT_PRESETS.get(lid) if item.get("auto_detectable") else None
            existing = await db.scalar(
                select(AIReviewChecklistItem).where(AIReviewChecklistItem.legacy_id == lid)
            )
            payload = dict(
                legacy_id=lid,
                category=item.get("category", ""),
                item=item.get("item", ""),
                description=item.get("description"),
                applicable_contracts=item.get("applicable_contracts"),
                risk_level=item.get("risk_level", "medium"),
                gate_id=item.get("gate_id", "gate_clause"),
                gate_priority=item.get("gate_priority", 0),
                auto_detectable=bool(item.get("auto_detectable")),
                detect_config=json.dumps(detect, ensure_ascii=False) if detect else None,
                enabled=True,
                version_tag=version,
            )
            if existing:
                for k, v in payload.items():
                    setattr(existing, k, v)
            else:
                db.add(AIReviewChecklistItem(**payload))

        labels = json.loads((GENERATED / "risk_labels.json").read_text(encoding="utf-8"))
        for item in labels.get("items", []):
            row = await db.get(AIRiskLabel, item["id"])
            if row:
                row.name = item.get("name", row.name)
                row.category = item.get("category")
                row.gate_id = item.get("gate_id")
                row.color = item.get("color")
                row.enabled = True
                row.version_tag = version
            else:
                db.add(
                    AIRiskLabel(
                        label_id=item["id"],
                        name=item["name"],
                        category=item.get("category"),
                        gate_id=item.get("gate_id"),
                        color=item.get("color"),
                        enabled=True,
                        version_tag=version,
                    )
                )

        routing = json.loads((GENERATED / "revision_routing.json").read_text(encoding="utf-8"))
        from sqlalchemy import delete

        await db.execute(delete(AIRevisionRoutingRule))
        for idx, item in enumerate(routing.get("items", [])):
            db.add(
                AIRevisionRoutingRule(
                    issue_type=item.get("issue_type", ""),
                    default_method=item.get("default_method", "comment"),
                    auto_applicable=bool(item.get("auto_applicable", True)),
                    self_check_questions=item.get("self_check_questions") or "",
                    notes=item.get("notes") or "",
                    priority=idx,
                    enabled=True,
                    version_tag=version,
                )
            )

        for rule_def in DEFAULT_HARD_RULES:
            rule = dict(rule_def)
            existing = await db.scalar(select(AIHardRule).where(AIHardRule.rule_id == rule["rule_id"]))
            cfg = rule.pop("config_json")
            payload = {
                **rule,
                "config_json": json.dumps(cfg, ensure_ascii=False),
                "enabled": True,
                "version_tag": version,
            }
            if existing:
                for k, v in payload.items():
                    setattr(existing, k, v)
            else:
                db.add(AIHardRule(**payload))

        if LEGAL_PATH.is_file():
            snippets = json.loads(LEGAL_PATH.read_text(encoding="utf-8"))
            for sn in snippets:
                sid = sn.get("id", "")
                existing = await db.scalar(select(AILegalSnippet).where(AILegalSnippet.snippet_id == sid))
                kw = json.dumps(sn.get("keywords", []), ensure_ascii=False)
                if existing:
                    existing.keywords = kw
                    existing.text = sn.get("text", "")
                    existing.enabled = True
                    existing.version_tag = version
                else:
                    db.add(
                        AILegalSnippet(
                            snippet_id=sid,
                            keywords=kw,
                            text=sn.get("text", ""),
                            enabled=True,
                            version_tag=version,
                        )
                    )

        await db.commit()
        await refresh_config_cache(db)
    return version
