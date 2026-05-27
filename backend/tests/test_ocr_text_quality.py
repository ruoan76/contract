# -*- coding: utf-8 -*-
"""OCR 文本质量与解析回归测试。"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.ai_review.ocr_text_utils import (
    gibberish_ratio,
    indices_needing_ocr,
    page_needs_ocr,
)
from app.services.contract_parse_service import _mock_parse_fields
from app.services.parse_llm_service import detect_party_parse_warning, fuzzy_match_counterparty_names

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ocr" / "golden_samples.json"


def _load_samples() -> list[dict]:
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


@pytest.mark.parametrize("sample", _load_samples(), ids=lambda s: s["id"])
def test_golden_gibberish_and_party_warning(sample: dict) -> None:
    text = sample["text"]
    ratio = gibberish_ratio(text)
    if "gibberish_ratio_max" in sample:
        assert ratio <= sample["gibberish_ratio_max"], f"ratio={ratio}"
    if "gibberish_ratio_min" in sample:
        assert ratio >= sample["gibberish_ratio_min"], f"ratio={ratio}"

    if "page_needs_ocr" in sample:
        assert page_needs_ocr(text, min_chars=50, gibberish_threshold=0.35) is sample[
            "page_needs_ocr"
        ]

    fields = _mock_parse_fields(text, "test.pdf")
    if "party_parse_warning" in sample:
        assert fields["party_parse_warning"] is sample["party_parse_warning"]
    if "party_a" in sample:
        assert fields.get("party_a") == sample["party_a"]
    if "party_b" in sample:
        assert fields.get("party_b") == sample["party_b"]
    if "party_b_substr" in sample:
        assert sample["party_b_substr"] in (fields.get("party_b") or "")


def test_indices_needing_ocr_mixed_pages() -> None:
    pages = [
        "甲方：甘肃省烟草公司兰州市公司\n乙方：浪潮软件股份有限公司\n" * 3,
        "@@@乱码页###",
        "",
    ]
    need = indices_needing_ocr(pages, min_chars=50, gibberish_threshold=0.35)
    assert 1 in need
    assert 2 in need
    assert 0 not in need


def test_detect_party_parse_warning_patterns() -> None:
    assert detect_party_parse_warning("浪潮软住股俭直限公司", None) is True
    assert detect_party_parse_warning("浪潮软件股份有限公司", "得力集团") is False


@pytest.mark.asyncio
async def test_fuzzy_match_counterparty(db_session) -> None:
    from app.models.counterparty import Counterparty

    db_session.add(
        Counterparty(name="浪潮软件股份有限公司", credit_code="91110000123456789X", status=1)
    )
    await db_session.commit()

    party_a, party_b, corrections = await fuzzy_match_counterparty_names(
        db_session,
        "甘肃省烟草公司兰州市公司",
        "浪潮软住股俭直限公司",
        threshold=0.6,
    )
    assert party_b == "浪潮软件股份有限公司"
    assert corrections


@pytest.mark.asyncio
async def test_pdf_partial_page_ocr(tmp_path) -> None:
    """混合 PDF：乱码页应触发逐页 OCR。"""
    import fitz

    from app.services.ai_review.text_extractor import _extract_pdf

    pdf_path = tmp_path / "mixed.pdf"
    doc = fitz.open()
    page1 = doc.new_page()
    page1.insert_text((72, 72), "甲方：测试公司\n" * 20)
    doc.new_page()  # 空白扫描页
    doc.save(str(pdf_path))
    doc.close()

    fake_ocr = ["", "乙方：OCR识别公司"]

    with patch("app.services.ai_review.text_extractor.settings") as mock_settings:
        mock_settings.AI_OCR_ENABLED = True
        mock_settings.AI_OCR_MIN_CHARS = 200
        mock_settings.AI_OCR_PAGE_MIN_CHARS = 50
        mock_settings.AI_OCR_GIBBERISH_RATIO = 0.35
        mock_settings.AI_OCR_MAX_PAGES = 40

        with patch(
            "app.services.ai_review.ocr.ocr_pdf_page_indices",
            return_value=fake_ocr,
        ) as mock_partial:
            result = await _extract_pdf(pdf_path, "pdf")

    mock_partial.assert_called_once()
    assert result.metadata.get("ocr_used") is True
    assert "OCR识别公司" in result.full_text
