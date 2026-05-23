# -*- coding: utf-8 -*-
"""
AI 审查演示结果（含 label_id / gate_id / revision_method）。
正式环境由审查引擎写入 DB；当前无 DB 时供联调与契约对齐。
"""

from fastapi import APIRouter

router = APIRouter()

# 与原型 page-ai-review 风险项一致
DEMO_ISSUES = [
    {
        "clause_ref": "第四条 违约责任",
        "title": "赔偿无上限",
        "risk_level": "high",
        "confidence": 0.92,
        "dimension": "risk_assessment",
        "label_id": "L08",
        "label_name": "违约责任",
        "gate_id": "gate_clause",
        "revision_method": "comment",
        "cuad_code": "CUAD-13",
        "description": "条款未设置赔偿上限，存在无限责任风险。",
        "legal_basis": "《民法典》第 584 条",
    },
    {
        "clause_ref": "第六条 管辖约定",
        "title": "异地管辖",
        "risk_level": "high",
        "confidence": 0.95,
        "dimension": "risk_assessment",
        "label_id": "L11",
        "label_name": "争议解决",
        "gate_id": "gate_clause",
        "revision_method": "comment",
        "cuad_code": "CUAD-19",
        "description": "约定对方所在地法院管辖，增加维权成本。",
        "legal_basis": "《民事诉讼法》第 35 条",
    },
    {
        "clause_ref": "第三条 付款条件",
        "title": "预付款比例偏高",
        "risk_level": "medium",
        "confidence": 0.88,
        "dimension": "finance_check",
        "label_id": "L06",
        "label_name": "价款与支付",
        "gate_id": "gate_clause",
        "revision_method": "comment",
        "cuad_code": "CUAD-07",
        "description": "预付款比例 40%，建议控制在 30% 以内。",
        "legal_basis": "内部财务制度",
    },
    {
        "clause_ref": "第七条 验收标准",
        "title": "表述模糊",
        "risk_level": "medium",
        "confidence": 0.65,
        "dimension": "performance_check",
        "label_id": "L07",
        "label_name": "交付与验收",
        "gate_id": "gate_clause",
        "revision_method": "comment",
        "cuad_code": None,
        "description": "验收条件未量化，易产生履约争议。",
        "legal_basis": "《民法典》第 510 条",
    },
    {
        "clause_ref": "第八条 知识产权归属",
        "title": "约定不明",
        "risk_level": "medium",
        "confidence": 0.52,
        "dimension": "compliance_check",
        "label_id": "L12",
        "label_name": "知识产权与保密",
        "gate_id": "gate_clause",
        "revision_method": "comment",
        "cuad_code": "CUAD-15",
        "description": "知识产权归属约定不明，建议法务重点复核。",
        "legal_basis": "《民法典》第 123 条",
    },
    {
        "clause_ref": "第五条 保密条款",
        "title": "条款完整",
        "risk_level": "low",
        "confidence": 0.96,
        "dimension": "compliance_check",
        "label_id": "L12",
        "label_name": "知识产权与保密",
        "gate_id": "gate_clause",
        "revision_method": "track_changes",
        "cuad_code": None,
        "description": "保密期限与范围符合行业标准。",
        "legal_basis": "《反不正当竞争法》第 9 条",
    },
]

DEMO_GATES = {
    "gate_validity": {"status": "pass", "summary": "未发现效力致命问题"},
    "gate_subject": {"status": "pass", "summary": "签约主体与授权项已核对（示意）"},
    "gate_clause": {"status": "warn", "summary": "4 项条款风险待处理"},
    "gate_consistency": {"status": "pass", "summary": "正文与附件金额一致"},
    "gate_output": {"status": "pending", "summary": "待法务确认后输出终稿"},
}


@router.get("/demo/result", summary="演示审查结果（含扩展字段）")
async def demo_review_result():
    return {
        "code": 200,
        "data": {
            "review_id": "REV-DEMO-001",
            "status": "ai_done",
            "overall": {
                "risk_level": "medium",
                "risk_score": 65,
                "recommendation": "建议修改关键条款后签署",
            },
            "gates": DEMO_GATES,
            "issues": DEMO_ISSUES,
            "dimensions": {
                "compliance_check": 85,
                "risk_assessment": 42,
                "finance_check": 68,
                "performance_check": 78,
                "anomaly_detection": 90,
            },
        },
    }
