"""AI 审查报告生成 — PDF / HTML / JSON"""
from __future__ import annotations

import json
import logging
from io import BytesIO
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import AIReview

logger = logging.getLogger(__name__)


def _parse_json(raw: str | None) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


async def get_review_report_data(db: AsyncSession, review_id: str) -> dict:
    """加载审查记录并组装报告数据。"""
    result = await db.execute(select(AIReview).where(AIReview.review_id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise ValueError("审查记录不存在")

    return {
        "review_id": review.review_id,
        "contract_id": review.contract_id,
        "status": review.review_status,
        "overall_risk_level": review.overall_risk_level,
        "overall_risk_score": review.overall_risk_score,
        "recommendation": review.recommendation,
        "clause_reviews": _parse_json(review.clause_reviews),
        "rule_violations": _parse_json(review.rule_violations),
        "summary": _parse_json(review.summary),
        "model_version": review.model_version,
        "review_duration_seconds": review.review_duration_seconds,
        "created_at": review.created_at.isoformat() if review.created_at else None,
    }


def _build_pdf_bytes(data: dict) -> bytes:
    """使用 reportlab 生成简单 PDF。"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 20 * mm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(20 * mm, y, "AI Contract Review Report")
    y -= 12 * mm

    c.setFont("Helvetica", 11)
    lines = [
        f"Review ID: {data.get('review_id', '-')}",
        f"Contract ID: {data.get('contract_id', '-')}",
        f"Status: {data.get('status', '-')}",
        f"Risk Level: {data.get('overall_risk_level', '-')}",
        f"Risk Score: {data.get('overall_risk_score', '-')}",
        f"Recommendation: {data.get('recommendation') or '-'}",
        f"Model: {data.get('model_version') or '-'}",
        f"Created: {data.get('created_at') or '-'}",
    ]
    for line in lines:
        c.drawString(20 * mm, y, str(line)[:90])
        y -= 7 * mm

    violations = data.get("rule_violations") or []
    if violations:
        y -= 5 * mm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20 * mm, y, "Rule Violations")
        y -= 8 * mm
        c.setFont("Helvetica", 10)
        for item in violations[:10]:
            text = json.dumps(item, ensure_ascii=False) if isinstance(item, dict) else str(item)
            c.drawString(25 * mm, y, text[:85])
            y -= 6 * mm
            if y < 30 * mm:
                c.showPage()
                y = height - 20 * mm
                c.setFont("Helvetica", 10)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()


def _build_html(data: dict) -> str:
    """HTML 报告兜底。"""
    violations = data.get("rule_violations") or []
    violation_rows = "".join(
        f"<li>{json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v}</li>"
        for v in violations[:20]
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><title>审查报告 {data.get('review_id', '')}</title></head>
<body>
<h1>AI 合同审查报告</h1>
<ul>
  <li>审查 ID: {data.get('review_id')}</li>
  <li>合同 ID: {data.get('contract_id')}</li>
  <li>状态: {data.get('status')}</li>
  <li>风险等级: {data.get('overall_risk_level')}</li>
  <li>风险评分: {data.get('overall_risk_score')}</li>
  <li>建议: {data.get('recommendation') or '-'}</li>
</ul>
<h2>规则违规</h2>
<ul>{violation_rows or '<li>无</li>'}</ul>
</body>
</html>"""


async def generate_review_report(
    db: AsyncSession,
    review_id: str,
    fmt: str = "pdf",
) -> tuple[bytes | str | dict, str, str]:
    """
    生成审查报告。

    Returns:
        (content, media_type, filename)
    """
    data = await get_review_report_data(db, review_id)

    if fmt == "json":
        return data, "application/json", f"review-{review_id}.json"

    if fmt == "html":
        html = _build_html(data)
        return html, "text/html; charset=utf-8", f"review-{review_id}.html"

    # 默认 PDF
    try:
        pdf_bytes = _build_pdf_bytes(data)
        return pdf_bytes, "application/pdf", f"review-{review_id}.pdf"
    except ImportError:
        logger.warning("reportlab 未安装，回退 HTML 报告")
        html = _build_html(data)
        return html, "text/html; charset=utf-8", f"review-{review_id}.html"
    except Exception as exc:
        logger.warning("PDF 生成失败，回退 JSON: %s", exc)
        return data, "application/json", f"review-{review_id}.json"
