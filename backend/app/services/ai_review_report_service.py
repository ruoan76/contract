"""AI 审查报告生成 — PDF / HTML / JSON"""
from __future__ import annotations

import html
import json
import logging
from io import BytesIO
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import AIReview
from app.services.ai_review.checklist_matrix_service import build_checklist_matrix

logger = logging.getLogger(__name__)

_CN_FONT = "STSong-Light"
_CN_FONT_REGISTERED = False


def _parse_json(raw: str | None) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


def _ensure_cn_font() -> str:
    """注册 reportlab 内置简体中文字体。"""
    global _CN_FONT_REGISTERED
    if not _CN_FONT_REGISTERED:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont

        pdfmetrics.registerFont(UnicodeCIDFont(_CN_FONT))
        _CN_FONT_REGISTERED = True
    return _CN_FONT


def _risk_label(level: str | None) -> str:
    mapping = {
        "low": "低风险",
        "medium": "中风险",
        "high": "高风险",
        "critical": "极高风险",
    }
    return mapping.get((level or "").lower(), level or "-")


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
        "clause_reviews": _parse_json(review.clause_reviews) or [],
        "rule_violations": _parse_json(review.rule_violations) or [],
        "summary": _parse_json(review.summary) or {},
        "model_version": review.model_version,
        "review_duration_seconds": review.review_duration_seconds,
        "created_at": review.created_at.isoformat() if review.created_at else None,
    }


def _escape(text: Any) -> str:
    return html.escape(str(text or ""))


def _build_html(data: dict) -> str:
    """HTML 报告（含中文内容与条款列表）。"""
    summary = data.get("summary") or {}
    violations = data.get("rule_violations") or []
    clauses = data.get("clause_reviews") or []
    gates = summary.get("gates") or {}

    violation_rows = "".join(
        f"<li>{_escape(v.get('rule_name') if isinstance(v, dict) else v)} — "
        f"{_escape(v.get('message') if isinstance(v, dict) else '')}</li>"
        for v in violations[:20]
    )
    issue_rows = ""
    for item in clauses[:50]:
        if not isinstance(item, dict):
            continue
        issue_rows += (
            f"<tr><td>{_escape(item.get('clause'))}</td>"
            f"<td>{_escape(_risk_label(item.get('risk_level')))}</td>"
            f"<td>{_escape(item.get('description') or item.get('suggestion'))}</td>"
            f"<td>{_escape(item.get('evidence_quote'))}</td></tr>"
        )

    gate_rows = ""
    for gid, gate in gates.items():
        if isinstance(gate, dict):
            gate_rows += (
                f"<li>{_escape(gid)}: {_escape(gate.get('status'))} — "
                f"{_escape(gate.get('summary'))}</li>"
            )

    completeness = summary.get("review_completeness") or "-"
    matrix = build_checklist_matrix(summary, clauses)
    checklist_rows = ""
    fail_items: list[dict] = []
    for cat in matrix.get("categories") or []:
        for item in cat.get("items") or []:
            if item.get("conclusion") in ("fail", "attention"):
                fail_items.append(item)
    for item in fail_items[:25]:
        checklist_rows += (
            f"<tr><td>{item.get('id')}</td>"
            f"<td>{_escape(item.get('item'))}</td>"
            f"<td>{_escape(item.get('conclusion'))}</td>"
            f"<td>{_escape(_risk_label(item.get('risk_level')))}</td>"
            f"<td>{_escape(item.get('ai_suggestion'))}</td></tr>"
        )
    cov_rate = matrix.get("coverage_rate")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>审查报告 {_escape(data.get('review_id', ''))}</title>
<style>
body {{ font-family: "PingFang SC", "Microsoft YaHei", sans-serif; margin: 24px; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
th, td {{ border: 1px solid #ccc; padding: 6px 8px; font-size: 13px; vertical-align: top; }}
th {{ background: #f5f5f5; }}
h1 {{ font-size: 20px; }}
h2 {{ font-size: 16px; margin-top: 20px; }}
</style>
</head>
<body>
<h1>AI 合同审查报告</h1>
<ul>
  <li>审查 ID: {_escape(data.get('review_id'))}</li>
  <li>合同 ID: {_escape(data.get('contract_id'))}</li>
  <li>状态: {_escape(data.get('status'))}</li>
  <li>风险等级: {_escape(_risk_label(data.get('overall_risk_level')))}</li>
  <li>风险评分: {_escape(data.get('overall_risk_score'))}</li>
  <li>完整度: {_escape(completeness)}</li>
  <li>建议: {_escape(data.get('recommendation') or '-')}</li>
  <li>模型: {_escape(data.get('model_version') or '-')}</li>
  <li>生成时间: {_escape(data.get('created_at') or '-')}</li>
</ul>
<h2>五门禁</h2>
<ul>{gate_rows or '<li>无</li>'}</ul>
<h2>规则命中</h2>
<ul>{violation_rows or '<li>无</li>'}</ul>
<h2>审查清单（MLX 覆盖率 {cov_rate}，未通过/需关注前 25 项）</h2>
<table>
<thead><tr><th>ID</th><th>审查项</th><th>结论</th><th>风险</th><th>AI 建议</th></tr></thead>
<tbody>{checklist_rows or '<tr><td colspan="5">无</td></tr>'}</tbody>
</table>
<h2>条款风险（前 50 条）</h2>
<table>
<thead><tr><th>条款</th><th>风险</th><th>说明/建议</th><th>原文证据</th></tr></thead>
<tbody>{issue_rows or '<tr><td colspan="4">无</td></tr>'}</tbody>
</table>
</body>
</html>"""


def _build_pdf_bytes(data: dict) -> bytes:
    """使用 reportlab + STSong-Light 生成中文 PDF。"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib import colors

    font = _ensure_cn_font()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    title_style = ParagraphStyle("title", fontName=font, fontSize=16, leading=22, spaceAfter=8)
    h2_style = ParagraphStyle("h2", fontName=font, fontSize=13, leading=18, spaceBefore=10, spaceAfter=6)
    body_style = ParagraphStyle("body", fontName=font, fontSize=10, leading=14)
    cell_style = ParagraphStyle("cell", fontName=font, fontSize=9, leading=12)

    def p(text: Any, style=body_style) -> Paragraph:
        safe = _escape(text).replace("\n", "<br/>")
        return Paragraph(safe or "—", style)

    summary = data.get("summary") or {}
    story: list = [p("AI 合同审查报告", title_style), Spacer(1, 4 * mm)]

    meta_lines = [
        f"审查 ID：{data.get('review_id', '-')}",
        f"合同 ID：{data.get('contract_id', '-')}",
        f"状态：{data.get('status', '-')}",
        f"风险等级：{_risk_label(data.get('overall_risk_level'))}",
        f"风险评分：{data.get('overall_risk_score', '-')}",
        f"完整度：{summary.get('review_completeness', '-')}",
        f"模型：{data.get('model_version') or '-'}",
        f"生成时间：{data.get('created_at') or '-'}",
    ]
    for line in meta_lines:
        story.append(p(line))
    story.append(Spacer(1, 4 * mm))

    if data.get("recommendation"):
        story.append(p("总体建议", h2_style))
        story.append(p(data.get("recommendation")))

    gates = summary.get("gates") or {}
    if gates:
        story.append(p("五门禁", h2_style))
        for gid, gate in gates.items():
            if isinstance(gate, dict):
                story.append(p(f"{gid}：{gate.get('status', '-')} — {gate.get('summary', '')}"))

    violations = data.get("rule_violations") or []
    if violations:
        story.append(p("规则命中", h2_style))
        for item in violations[:15]:
            if isinstance(item, dict):
                story.append(
                    p(f"{item.get('rule_id', '')} {item.get('rule_name', '')}：{item.get('message', '')}")
                )

    clauses = data.get("clause_reviews") or []
    matrix = build_checklist_matrix(summary, clauses)
    fail_items: list[dict] = []
    for cat in matrix.get("categories") or []:
        for item in cat.get("items") or []:
            if item.get("conclusion") in ("fail", "attention"):
                fail_items.append(item)
    if fail_items:
        cov = matrix.get("coverage_rate")
        story.append(p(f"审查清单（MLX 覆盖率 {cov}，未通过/需关注）", h2_style))
        ck_rows = [
            [p("ID", cell_style), p("审查项", cell_style), p("结论", cell_style), p("建议", cell_style)]
        ]
        for item in fail_items[:20]:
            ck_rows.append(
                [
                    p(str(item.get("id")), cell_style),
                    p(item.get("item"), cell_style),
                    p(item.get("conclusion"), cell_style),
                    p(item.get("ai_suggestion"), cell_style),
                ]
            )
        ck_table = Table(ck_rows, colWidths=[12 * mm, 45 * mm, 18 * mm, 90 * mm])
        ck_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(ck_table)

    if clauses:
        story.append(p("条款风险（前 30 条）", h2_style))
        rows = [
            [
                p("条款", cell_style),
                p("风险", cell_style),
                p("说明", cell_style),
            ]
        ]
        for item in clauses[:30]:
            if not isinstance(item, dict):
                continue
            rows.append(
                [
                    p(item.get("clause") or item.get("title"), cell_style),
                    p(_risk_label(item.get("risk_level")), cell_style),
                    p(item.get("description") or item.get("suggestion"), cell_style),
                ]
            )
        table = Table(rows, colWidths=[45 * mm, 22 * mm, 98 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


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
        html_content = _build_html(data)
        return html_content, "text/html; charset=utf-8", f"review-{review_id}.html"

    try:
        pdf_bytes = _build_pdf_bytes(data)
        if not pdf_bytes.startswith(b"%PDF"):
            raise ValueError("PDF 生成结果无效")
        return pdf_bytes, "application/pdf", f"review-{review_id}.pdf"
    except ImportError as exc:
        logger.warning("reportlab 未安装，回退 HTML 报告: %s", exc)
        html_content = _build_html(data)
        return html_content, "text/html; charset=utf-8", f"review-{review_id}.html"
    except Exception as exc:
        logger.exception("PDF 生成失败，回退 HTML: %s", exc)
        html_content = _build_html(data)
        return html_content, "text/html; charset=utf-8", f"review-{review_id}.html"
