# -*- coding: utf-8 -*-
"""AI 审查报告 PDF 主题：色板、样式、页眉页脚。"""
from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm

CN_FONT = "STSong-Light"
_CN_FONT_REGISTERED = False

# 色板（与前端 Element Plus 风险色接近）
COLOR_PRIMARY = colors.HexColor("#2563eb")
COLOR_HEADER_BG = colors.HexColor("#1e3a5f")
COLOR_HEADER_FG = colors.white
COLOR_ZEBRA = colors.HexColor("#f9fafb")
COLOR_BORDER = colors.HexColor("#e5e7eb")
COLOR_MUTED = colors.HexColor("#6b7280")

RISK_COLORS: dict[str, tuple[Any, Any]] = {
    "critical": (colors.HexColor("#dc2626"), colors.HexColor("#fef2f2")),
    "high": (colors.HexColor("#ea580c"), colors.HexColor("#fff7ed")),
    "medium": (colors.HexColor("#ca8a04"), colors.HexColor("#fffbeb")),
    "low": (colors.HexColor("#16a34a"), colors.HexColor("#ecfdf5")),
}

GATE_LABELS: dict[str, str] = {
    "gate_validity": "效力",
    "gate_subject": "主体",
    "gate_clause": "条款",
    "gate_consistency": "一致性",
    "gate_output": "输出",
}

GATE_ORDER = [
    "gate_validity",
    "gate_subject",
    "gate_clause",
    "gate_consistency",
    "gate_output",
]

GATE_STATUS_BG: dict[str, Any] = {
    "pass": colors.HexColor("#ecfdf5"),
    "fail": colors.HexColor("#fef2f2"),
    "warn": colors.HexColor("#fffbeb"),
    "warning": colors.HexColor("#fffbeb"),
    "pending": colors.HexColor("#f9fafb"),
}

HEADER_TEXT = "合同审批平台 · AI 审查报告"
FOOTER_TEXT = "本报告由 AI 辅助生成，仅供内部评审参考，不构成法律意见。"

PAGE_MARGIN_LEFT = 18 * mm
PAGE_MARGIN_RIGHT = 18 * mm
PAGE_MARGIN_TOP = 28 * mm
PAGE_MARGIN_BOTTOM = 22 * mm
CONTENT_WIDTH = 210 * mm - PAGE_MARGIN_LEFT - PAGE_MARGIN_RIGHT


def ensure_cn_font() -> str:
    """注册 reportlab 内置简体中文字体。"""
    global _CN_FONT_REGISTERED
    if not _CN_FONT_REGISTERED:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont

        pdfmetrics.registerFont(UnicodeCIDFont(CN_FONT))
        _CN_FONT_REGISTERED = True
    return CN_FONT


def risk_label(level: str | None) -> str:
    mapping = {
        "low": "低风险",
        "medium": "中风险",
        "high": "高风险",
        "critical": "极高风险",
    }
    return mapping.get((level or "").lower(), level or "—")


def risk_colors(level: str | None) -> tuple[Any, Any]:
    key = (level or "").lower()
    return RISK_COLORS.get(key, (COLOR_MUTED, colors.HexColor("#f3f4f6")))


def gate_bg(status: str | None) -> Any:
    return GATE_STATUS_BG.get((status or "pending").lower(), GATE_STATUS_BG["pending"])


def escape_pdf_text(text: Any) -> str:
    return html.escape(str(text or ""))


def truncate_cell(text: Any, max_len: int = 500) -> str:
    raw = str(text or "").strip()
    if len(raw) <= max_len:
        return raw
    return raw[: max_len - 8] + "…（已截断）"


@dataclass
class ReportPdfStyles:
    cover_title: ParagraphStyle
    cover_sub: ParagraphStyle
    section_h2: ParagraphStyle
    body: ParagraphStyle
    body_muted: ParagraphStyle
    table_header: ParagraphStyle
    table_cell: ParagraphStyle
    risk_badge: ParagraphStyle
    quote: ParagraphStyle


def build_pdf_styles(font: str) -> ReportPdfStyles:
    return ReportPdfStyles(
        cover_title=ParagraphStyle(
            "CoverTitle",
            fontName=font,
            fontSize=22,
            leading=28,
            spaceAfter=6,
            textColor=COLOR_HEADER_BG,
        ),
        cover_sub=ParagraphStyle(
            "CoverSub",
            fontName=font,
            fontSize=11,
            leading=15,
            textColor=COLOR_MUTED,
            spaceAfter=4,
        ),
        section_h2=ParagraphStyle(
            "SectionH2",
            fontName=font,
            fontSize=13,
            leading=18,
            spaceBefore=12,
            spaceAfter=6,
            textColor=COLOR_HEADER_BG,
        ),
        body=ParagraphStyle(
            "Body",
            fontName=font,
            fontSize=10,
            leading=14,
        ),
        body_muted=ParagraphStyle(
            "BodyMuted",
            fontName=font,
            fontSize=9,
            leading=12,
            textColor=COLOR_MUTED,
        ),
        table_header=ParagraphStyle(
            "TableHeader",
            fontName=font,
            fontSize=9,
            leading=12,
            textColor=COLOR_HEADER_FG,
        ),
        table_cell=ParagraphStyle(
            "TableCell",
            fontName=font,
            fontSize=9,
            leading=12,
            wordWrap="CJK",
        ),
        risk_badge=ParagraphStyle(
            "RiskBadge",
            fontName=font,
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),
        quote=ParagraphStyle(
            "Quote",
            fontName=font,
            fontSize=10,
            leading=14,
            leftIndent=8,
            borderPadding=4,
        ),
    )


def draw_page_header_footer(canvas: Any, doc: Any) -> None:
    """每页页眉页脚。"""
    canvas.saveState()
    page_num = canvas.getPageNumber()
    w, _h = doc.pagesize

    canvas.setStrokeColor(COLOR_BORDER)
    canvas.setLineWidth(0.5)
    header_y = doc.pagesize[1] - 14 * mm
    canvas.line(PAGE_MARGIN_LEFT, header_y, w - PAGE_MARGIN_RIGHT, header_y)

    canvas.setFont(CN_FONT, 8)
    canvas.setFillColor(COLOR_MUTED)
    canvas.drawString(PAGE_MARGIN_LEFT, header_y + 3 * mm, HEADER_TEXT)
    canvas.drawRightString(w - PAGE_MARGIN_RIGHT, header_y + 3 * mm, f"第 {page_num} 页")

    footer_y = 12 * mm
    canvas.line(PAGE_MARGIN_LEFT, footer_y + 6 * mm, w - PAGE_MARGIN_RIGHT, footer_y + 6 * mm)
    canvas.setFont(CN_FONT, 7)
    canvas.drawCentredString(w / 2, footer_y, FOOTER_TEXT)
    canvas.restoreState()


def standard_table_style(font: str, *, col_count: int, header_rows: int = 1) -> list[tuple]:
    """表头深色 + 斑马纹 + 网格。"""
    cmds: list[tuple] = [
        ("FONTNAME", (0, 0), (-1, -1), font),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, COLOR_BORDER),
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), COLOR_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), COLOR_HEADER_FG),
        ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [colors.white, COLOR_ZEBRA]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if col_count > 0:
        cmds.append(("ALIGN", (0, 0), (-1, -1), "LEFT"))
    return cmds
