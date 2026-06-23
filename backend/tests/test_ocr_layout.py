# -*- coding: utf-8 -*-
"""OCR 版面重建与文本规范化单测。"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.ai_review.ocr_layout import (
    detect_layout_suspect,
    layout_ocr_blocks,
    layout_ocr_blocks_with_meta,
    ocr_results_to_raw_text,
)
from app.services.ai_review.text_normalize import normalize_contract_text

_LANZHOU_PDF = (
    Path(__file__).resolve().parents[1]
    / "data/contract-files/contracts/CON-202605-0049"
    / "甘肃省烟草公司兰州市公司2018年卷烟营销网建信息化项目建设合同-195.8万.pdf"
)


def _bbox(cx: float, cy: float, w: float = 40, h: float = 12) -> list[list[float]]:
    return [
        [cx - w / 2, cy - h / 2],
        [cx + w / 2, cy - h / 2],
        [cx + w / 2, cy + h / 2],
        [cx - w / 2, cy + h / 2],
    ]


def test_layout_ocr_blocks_reading_order() -> None:
    """乱序 bbox 应输出自上而下、从左到右的阅读顺序。"""
    results = [
        (_bbox(200, 80), "乙方：测试公司", 0.9),
        (_bbox(50, 20), "采购合同", 0.95),
        (_bbox(50, 50), "甲方：甲方单位", 0.92),
        (_bbox(50, 110), "第一条", 0.88),
        (_bbox(50, 125), "总则内容", 0.87),
    ]
    text = layout_ocr_blocks(results, min_conf=0.5)
    lines = [ln for ln in text.split("\n") if ln.strip()]
    assert lines[0] == "采购合同"
    assert "甲方：甲方单位" in lines[1]
    assert "乙方：测试公司" in text
    assert "第一条" in text
    assert "总则内容" in text
    assert "\n\n第一条" in text or text.index("第一条") > 0


def test_layout_two_columns_left_then_right() -> None:
    """双栏应按左栏自上而下、再右栏，避免按 Y 交错。"""
    results = [
        (_bbox(320, 30), "乙方：乙公司", 0.9),
        (_bbox(60, 25), "甲方：甲公司", 0.92),
        (_bbox(320, 70), "乙方地址", 0.88),
        (_bbox(60, 65), "甲方地址", 0.9),
    ]
    text = layout_ocr_blocks(results, min_conf=0.5)
    assert text.index("甲方") < text.index("乙方")
    assert text.index("甲方地址") < text.index("乙方地址")


def test_layout_merges_same_line_fragments() -> None:
    """同一行 Y 接近的块应合并为一行。"""
    results = [
        (_bbox(30, 40), "合同", 0.9),
        (_bbox(80, 41), "金额", 0.9),
        (_bbox(130, 39), "80000元", 0.9),
    ]
    text = layout_ocr_blocks(results, min_conf=0.5)
    assert "合同" in text and "金额" in text and "80000元" in text


def test_detect_layout_suspect_inverted_legal_order() -> None:
    bad = "双方协商一致的基础上，根据《中华人民共和国合同法》签订本合同。"
    good = "根据《中华人民共和国合同法》，双方协商一致的基础上签订本合同。"
    assert detect_layout_suspect(bad) is True
    assert detect_layout_suspect(good) is False


def test_layout_ocr_blocks_with_meta_lines_bbox() -> None:
    results = [(_bbox(50, 20), "第一条", 0.9)]
    meta = layout_ocr_blocks_with_meta(results, min_conf=0.5)
    assert meta.lines
    assert meta.lines[0].bbox is not None


def test_ocr_results_to_raw_text_detection_order() -> None:
    results = [
        (_bbox(200, 80), "B", 0.9),
        (_bbox(50, 20), "A", 0.9),
    ]
    assert ocr_results_to_raw_text(results, min_conf=0.5) == "B\nA"


def test_normalize_contract_text() -> None:
    raw = "甲方:  测试公司  \n\n\n第二条  内容"
    out = normalize_contract_text(raw)
    assert "甲方：" in out
    assert "测试公司" in out
    assert "\n\n" in out
    assert "  " not in out.replace("\n", "")


def test_join_page_text_ocr_markers() -> None:
    from app.services.ai_review.text_extractor import _join_page_text

    joined = _join_page_text(["第一页正文", "第二页正文"], ocr_used=True)
    assert "--- 第 1 页 ---" in joined
    assert "--- 第 2 页 ---" in joined
    assert "第一页正文" in joined
    assert "\n\n" in joined

    plain = _join_page_text(["a", "b"], ocr_used=False)
    assert "--- 第" not in plain


@pytest.mark.slow
def test_lanzhou_contract_page2_legal_phrase_order() -> None:
    """真实扫描件第 2 页：法律援引应出现在「协商一致」之前（若 OCR 可用）。"""
    if not _LANZHOU_PDF.exists():
        pytest.skip("兰州合同样例 PDF 不存在")

    from app.core.config import settings

    if not settings.AI_OCR_ENABLED:
        pytest.skip("OCR 未启用")

    from app.services.ai_review.ocr import ocr_pdf_page_indices

    pages = ocr_pdf_page_indices(_LANZHOU_PDF, [1], max_pages=5)
    text = pages[0] if pages else ""
    if not text.strip():
        pytest.skip("OCR 未产出文本")

    ref = "根据《"
    consensus = "协商一致"
    if ref not in text or consensus not in text:
        pytest.skip("本页未包含预期法律套话，跳过句序断言")

    assert text.index(ref) < text.index(consensus), (
        "排版后「根据《…》」应早于「协商一致」；"
        f"片段: {text[text.index(consensus) - 40 : text.index(consensus) + 80]!r}"
    )
