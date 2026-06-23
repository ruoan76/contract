"""AI 审查报告生成 — PDF / HTML / JSON"""
from __future__ import annotations

import html
import json
import logging
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import AIReview, Contract
from app.services.ai_review.checklist_matrix_service import build_checklist_matrix
from app.services.ai_review.report_pdf_theme import (
    CONTENT_WIDTH,
    GATE_LABELS,
    GATE_ORDER,
    PAGE_MARGIN_BOTTOM,
    PAGE_MARGIN_LEFT,
    PAGE_MARGIN_RIGHT,
    PAGE_MARGIN_TOP,
    build_pdf_styles,
    draw_page_header_footer,
    ensure_cn_font,
    escape_pdf_text,
    gate_bg,
    risk_colors,
    risk_label,
    standard_table_style,
    truncate_cell,
)

logger = logging.getLogger(__name__)


def _parse_json(raw: str | None) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


def _escape(text: Any) -> str:
    return html.escape(str(text or ""))


async def get_review_report_data(db: AsyncSession, review_id: str) -> dict:
    """加载审查记录并组装报告数据。"""
    result = await db.execute(select(AIReview).where(AIReview.review_id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise ValueError("审查记录不存在")

    data: dict[str, Any] = {
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

    if review.contract_id:
        try:
            c_res = await db.execute(select(Contract).where(Contract.id == review.contract_id))
            contract = c_res.scalar_one_or_none()
            if contract:
                data["contract_title"] = contract.title
                data["contract_no"] = contract.contract_no
                data["counterparty_name"] = contract.counterparty_name
        except Exception as exc:
            logger.debug("报告加载合同元信息失败: %s", exc)

    return data


def _paragraph(text: Any, style, *, truncate: int | None = None) -> Paragraph:
    raw = truncate_cell(text, truncate) if truncate else str(text or "")
    safe = escape_pdf_text(raw).replace("\n", "<br/>")
    return Paragraph(safe or "—", style)


def _build_html(data: dict) -> str:
    """HTML 报告（视觉与 PDF 版式对齐，供回退或浏览器打印）。"""
    summary = data.get("summary") or {}
    violations = data.get("rule_violations") or []
    clauses = data.get("clause_reviews") or []
    gates = summary.get("gates") or {}
    level = (data.get("overall_risk_level") or "").lower()
    risk_cls = level if level in ("critical", "high", "medium", "low") else "medium"
    completeness = summary.get("review_completeness") or "-"
    matrix = build_checklist_matrix(summary, clauses)
    cov_rate = matrix.get("coverage_rate")

    meta_rows = [
        ("合同名称", data.get("contract_title") or "—"),
        ("合同编号", data.get("contract_no") or "—"),
        ("相对方", data.get("counterparty_name") or "—"),
        ("审查 ID", data.get("review_id")),
        ("合同 ID", data.get("contract_id")),
        ("状态", data.get("status")),
        ("模型", data.get("model_version") or "—"),
        ("生成时间", data.get("created_at") or "—"),
    ]
    meta_html = "".join(
        f"<tr><th>{_escape(k)}</th><td>{_escape(v)}</td></tr>" for k, v in meta_rows
    )

    gate_cells = ""
    for gid in GATE_ORDER:
        gate = gates.get(gid) if isinstance(gates, dict) else None
        if not isinstance(gate, dict):
            continue
        status = (gate.get("status") or "pending").lower()
        gate_cells += (
            f'<div class="gate-cell gate-{status}">'
            f'<div class="gate-label">{_escape(GATE_LABELS.get(gid, gid))}</div>'
            f'<div class="gate-status">{_escape(gate.get("summary") or gate.get("status") or "—")}</div>'
            f"</div>"
        )
    if not gate_cells:
        gate_cells = '<div class="gate-empty">无门禁数据</div>'

    violation_rows = "".join(
        f"<li>{_escape(v.get('rule_name') if isinstance(v, dict) else v)} — "
        f"{_escape(v.get('message') if isinstance(v, dict) else '')}</li>"
        for v in violations[:20]
    )

    fail_items: list[dict] = []
    for cat in matrix.get("categories") or []:
        for item in cat.get("items") or []:
            if item.get("conclusion") in ("fail", "attention"):
                fail_items.append(item)
    checklist_rows = ""
    for item in fail_items[:25]:
        rl = (item.get("risk_level") or "").lower()
        checklist_rows += (
            f'<tr><td>{item.get("id")}</td>'
            f"<td>{_escape(item.get('item'))}</td>"
            f"<td>{_escape(item.get('conclusion'))}</td>"
            f'<td><span class="risk-text risk-{rl}">{_escape(risk_label(item.get("risk_level")))}</span></td>'
            f"<td>{_escape(item.get('ai_suggestion'))}</td></tr>"
        )

    issue_rows = ""
    for item in clauses[:50]:
        if not isinstance(item, dict):
            continue
        rl = (item.get("risk_level") or "").lower()
        issue_rows += (
            f"<tr><td>{_escape(item.get('clause'))}</td>"
            f'<td><span class="risk-text risk-{rl}">{_escape(risk_label(item.get("risk_level")))}</span></td>'
            f"<td>{_escape(item.get('description') or item.get('suggestion'))}</td>"
            f"<td>{_escape(item.get('evidence_quote'))}</td></tr>"
        )

    rec_block = ""
    if data.get("recommendation"):
        rec_block = f'<div class="quote-block">{_escape(data.get("recommendation"))}</div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>审查报告 {_escape(data.get('review_id', ''))}</title>
<style>
body {{ font-family: "PingFang SC", "Microsoft YaHei", sans-serif; margin: 0; color: #111827; }}
.cover {{ background: linear-gradient(135deg, #eff6ff 0%, #fff 60%); padding: 28px 32px; border-bottom: 3px solid #2563eb; }}
.cover-brand {{ font-size: 12px; color: #6b7280; margin-bottom: 8px; }}
.cover h1 {{ font-size: 24px; margin: 0 0 16px; color: #1e3a5f; }}
.risk-summary {{ display: flex; gap: 16px; align-items: stretch; margin: 16px 0; }}
.risk-badge {{ flex: 0 0 140px; padding: 16px; border-radius: 8px; text-align: center; font-size: 18px; font-weight: 700; color: #fff; }}
.risk-badge.critical {{ background: #dc2626; }}
.risk-badge.high {{ background: #ea580c; }}
.risk-badge.medium {{ background: #ca8a04; }}
.risk-badge.low {{ background: #16a34a; }}
.risk-meta {{ flex: 1; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; font-size: 14px; }}
.content {{ padding: 24px 32px; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
th, td {{ border: 1px solid #e5e7eb; padding: 8px 10px; font-size: 13px; vertical-align: top; }}
th {{ background: #1e3a5f; color: #fff; font-weight: 600; }}
tbody tr:nth-child(even) {{ background: #f9fafb; }}
h2 {{ font-size: 16px; margin-top: 24px; color: #1e3a5f; border-left: 4px solid #2563eb; padding-left: 8px; }}
.meta-table th {{ width: 120px; background: #f3f4f6; color: #374151; }}
.gate-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin-top: 12px; }}
.gate-cell {{ padding: 10px; border-radius: 6px; border: 1px solid #e5e7eb; font-size: 12px; }}
.gate-label {{ color: #6b7280; margin-bottom: 4px; }}
.gate-status {{ font-weight: 600; }}
.gate-pass {{ background: #ecfdf5; border-color: #a7f3d0; }}
.gate-fail {{ background: #fef2f2; border-color: #fecaca; }}
.gate-warn, .gate-warning {{ background: #fffbeb; border-color: #fde68a; }}
.gate-pending {{ background: #f9fafb; }}
.quote-block {{ border-left: 4px solid #2563eb; background: #eff6ff; padding: 12px 16px; margin: 12px 0; font-size: 14px; }}
.risk-text.critical {{ color: #dc2626; font-weight: 600; }}
.risk-text.high {{ color: #ea580c; font-weight: 600; }}
.risk-text.medium {{ color: #ca8a04; }}
.risk-text.low {{ color: #16a34a; }}
.footer-note {{ margin-top: 32px; padding-top: 12px; border-top: 1px solid #e5e7eb; font-size: 11px; color: #9ca3af; text-align: center; }}
</style>
</head>
<body>
<div class="cover">
  <div class="cover-brand">合同审批平台 · AI 审查报告</div>
  <h1>AI 合同审查报告</h1>
  <table class="meta-table"><tbody>{meta_html}</tbody></table>
  <div class="risk-summary">
    <div class="risk-badge {risk_cls}">{_escape(risk_label(data.get('overall_risk_level')))}</div>
    <div class="risk-meta">
      <div>风险评分：<strong>{_escape(data.get('overall_risk_score'))}</strong></div>
      <div>完整度：{_escape(completeness)}</div>
    </div>
  </div>
  {rec_block}
</div>
<div class="content">
<h2>效力与门禁</h2>
<div class="gate-grid">{gate_cells}</div>
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
<p class="footer-note">本报告由 AI 辅助生成，仅供内部评审参考，不构成法律意见。</p>
</div>
</body>
</html>"""


def _build_pdf_bytes(data: dict) -> bytes:
    """使用 reportlab 生成带封面、门禁色块与页眉页脚的中文 PDF。"""
    font = ensure_cn_font()
    styles = build_pdf_styles(font)
    summary = data.get("summary") or {}
    clauses = data.get("clause_reviews") or []
    matrix = build_checklist_matrix(summary, clauses)

    buffer = BytesIO()
    doc = BaseDocTemplate(
        buffer,
        pagesize=(210 * mm, 297 * mm),
        leftMargin=PAGE_MARGIN_LEFT,
        rightMargin=PAGE_MARGIN_RIGHT,
        topMargin=PAGE_MARGIN_TOP,
        bottomMargin=PAGE_MARGIN_BOTTOM,
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="main",
    )
    doc.addPageTemplates(
        [PageTemplate(id="main", frames=[frame], onPage=draw_page_header_footer)]
    )

    def p(text: Any, style, *, truncate: int | None = None) -> Paragraph:
        return _paragraph(text, style, truncate=truncate)

    story: list = []

    # --- 封面 ---
    cover_block: list = [
        p("合同审批平台 · AI 审查报告", styles.cover_sub),
        p("AI 合同审查报告", styles.cover_title),
        Spacer(1, 4 * mm),
    ]

    meta_table_data = [
        [p("合同名称", styles.table_cell), p(data.get("contract_title") or "—", styles.table_cell)],
        [p("合同编号", styles.table_cell), p(data.get("contract_no") or "—", styles.table_cell)],
        [p("相对方", styles.table_cell), p(data.get("counterparty_name") or "—", styles.table_cell)],
        [p("审查 ID", styles.table_cell), p(data.get("review_id"), styles.table_cell)],
        [p("状态", styles.table_cell), p(data.get("status"), styles.table_cell)],
        [p("模型", styles.table_cell), p(data.get("model_version") or "—", styles.table_cell)],
        [p("生成时间", styles.table_cell), p(data.get("created_at") or "—", styles.table_cell)],
    ]
    meta_table = Table(meta_table_data, colWidths=[32 * mm, CONTENT_WIDTH - 32 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f3f4f6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    cover_block.append(meta_table)
    cover_block.append(Spacer(1, 6 * mm))

    level = (data.get("overall_risk_level") or "").lower()
    fg, bg = risk_colors(level)
    badge_style = ParagraphStyle(
        "RiskBadgeDynamic",
        parent=styles.risk_badge,
        textColor=fg,
        backColor=bg,
    )
    risk_summary = Table(
        [
            [
                p(risk_label(data.get("overall_risk_level")), badge_style),
                p(
                    f"风险评分：{data.get('overall_risk_score', '—')}<br/>"
                    f"完整度：{summary.get('review_completeness', '—')}",
                    styles.body,
                ),
            ]
        ],
        colWidths=[42 * mm, CONTENT_WIDTH - 42 * mm],
    )
    risk_summary.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font),
                ("BACKGROUND", (0, 0), (0, 0), bg),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#f9fafb")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#e5e7eb")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    cover_block.append(risk_summary)

    if data.get("recommendation"):
        cover_block.append(Spacer(1, 4 * mm))
        quote_table = Table(
            [[p(truncate_cell(data.get("recommendation"), 800), styles.quote)]],
            colWidths=[CONTENT_WIDTH],
        )
        quote_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                    ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#2563eb")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        cover_block.append(quote_table)

    story.append(KeepTogether(cover_block))
    story.append(PageBreak())

    # --- 五门禁 ---
    gates = summary.get("gates") or {}
    if isinstance(gates, dict) and gates:
        gate_row_labels = []
        gate_row_values = []
        gate_styles_cmds: list[tuple] = [
            ("FONTNAME", (0, 0), (-1, -1), font),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]
        col_w = CONTENT_WIDTH / 5
        for col_idx, gid in enumerate(GATE_ORDER):
            gate = gates.get(gid)
            if not isinstance(gate, dict):
                gate = {"status": "pending", "summary": "—"}
            status = gate.get("status") or "pending"
            gate_row_labels.append(p(GATE_LABELS.get(gid, gid), styles.body_muted))
            gate_row_values.append(
                p(gate.get("summary") or status, styles.table_cell)
            )
            gate_styles_cmds.append(("BACKGROUND", (col_idx, 0), (col_idx, 0), colors.HexColor("#f9fafb")))
            gate_styles_cmds.append(("BACKGROUND", (col_idx, 1), (col_idx, 1), gate_bg(status)))
        gate_table = Table(
            [gate_row_labels, gate_row_values],
            colWidths=[col_w] * 5,
        )
        gate_table.setStyle(TableStyle(gate_styles_cmds))
        story.append(KeepTogether([p("效力与门禁", styles.section_h2), gate_table]))
        story.append(Spacer(1, 6 * mm))

    # --- 规则命中 ---
    violations = data.get("rule_violations") or []
    if violations:
        viol_block = [p("规则命中", styles.section_h2)]
        for item in violations[:15]:
            if isinstance(item, dict):
                viol_block.append(
                    p(
                        f"• {item.get('rule_id', '')} {item.get('rule_name', '')}："
                        f"{item.get('message', '')}",
                        styles.body,
                    )
                )
        story.append(KeepTogether(viol_block))
        story.append(Spacer(1, 4 * mm))

    # --- 审查清单 ---
    fail_items: list[dict] = []
    for cat in matrix.get("categories") or []:
        for item in cat.get("items") or []:
            if item.get("conclusion") in ("fail", "attention"):
                fail_items.append(item)
    if fail_items:
        cov = matrix.get("coverage_rate")
        ck_header = [
            p("ID", styles.table_header),
            p("审查项", styles.table_header),
            p("结论", styles.table_header),
            p("风险", styles.table_header),
            p("AI 建议", styles.table_header),
        ]
        ck_rows = [ck_header]
        for item in fail_items[:20]:
            rl = item.get("risk_level")
            risk_p_style = ParagraphStyle(
                "CellRisk",
                parent=styles.table_cell,
                textColor=risk_colors(rl)[0],
            )
            ck_rows.append(
                [
                    p(str(item.get("id")), styles.table_cell),
                    p(item.get("item"), styles.table_cell, truncate=400),
                    p(item.get("conclusion"), styles.table_cell),
                    p(risk_label(rl), risk_p_style),
                    p(item.get("ai_suggestion"), styles.table_cell, truncate=400),
                ]
            )
        ck_table = Table(
            ck_rows,
            colWidths=[14 * mm, 48 * mm, 18 * mm, 22 * mm, CONTENT_WIDTH - 102 * mm],
            repeatRows=1,
        )
        ck_cmds = standard_table_style(font, col_count=5)
        ck_table.setStyle(TableStyle(ck_cmds))
        story.append(
            KeepTogether(
                [
                    p(f"审查清单（MLX 覆盖率 {cov}，未通过/需关注）", styles.section_h2),
                    p("以下为需重点跟进项，完整清单见系统审查矩阵。", styles.body_muted),
                    ck_table,
                ]
            )
        )
        story.append(Spacer(1, 6 * mm))

    # --- 条款风险 ---
    if clauses:
        clause_header = [
            p("条款", styles.table_header),
            p("风险", styles.table_header),
            p("说明/建议", styles.table_header),
        ]
        rows = [clause_header]
        for item in clauses[:30]:
            if not isinstance(item, dict):
                continue
            rl = item.get("risk_level")
            risk_p_style = ParagraphStyle(
                "ClauseRisk",
                parent=styles.table_cell,
                textColor=risk_colors(rl)[0],
            )
            rows.append(
                [
                    p(item.get("clause") or item.get("title"), styles.table_cell),
                    p(risk_label(rl), risk_p_style),
                    p(
                        item.get("description") or item.get("suggestion"),
                        styles.table_cell,
                        truncate=500,
                    ),
                ]
            )
        clause_table = Table(
            rows,
            colWidths=[40 * mm, 24 * mm, CONTENT_WIDTH - 64 * mm],
            repeatRows=1,
        )
        clause_table.setStyle(TableStyle(standard_table_style(font, col_count=3)))
        story.append(
            KeepTogether(
                [
                    p("条款风险（前 30 条）", styles.section_h2),
                    clause_table,
                ]
            )
        )

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
