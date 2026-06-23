# -*- coding: utf-8 -*-
"""合同标题抽取与解析置信度测试。"""
from __future__ import annotations

import pytest

from app.services.ai_review.heading_utils import is_bad_title
from app.services.contract_parse_service import (
    _compute_parse_confidence,
    _mock_parse_fields,
    extract_contract_title,
)


class TestExtractContractTitle:
    def test_skips_page_marker_prefers_contract_line(self) -> None:
        text = (
            "--- 第 1 页 ---\n\n"
            "甘肃省烟草公司兰州市公司2018年卷烟营销网建信息化项目建设合同\n"
            "甲方：甘肃省烟草公司兰州市公司\n"
        )
        title, source = extract_contract_title(text, "upload.pdf")
        assert "项目建设合同" in title
        assert source == "body"
        assert not is_bad_title(title)

    def test_filename_fallback_when_only_page_marker(self) -> None:
        text = "--- 第 1 页 ---\n"
        filename = "甘肃省烟草公司兰州市公司2018年卷烟营销网建信息化项目建设合同-195.8万.pdf"
        title, source = extract_contract_title(text, filename)
        assert "项目建设合同" in title
        assert "195.8万" not in title
        assert source == "filename"

    def test_first_valid_line_when_no_contract_keyword(self) -> None:
        text = "某某采购框架协议\n甲方：A公司\n"
        title, source = extract_contract_title(text, "x.pdf")
        assert title == "某某采购框架协议"
        assert source == "body"

    def test_mock_parse_fields_not_page_marker(self) -> None:
        text = (
            "--- 第 1 页 ---\n\n"
            "甘肃省烟草公司兰州市公司2018年卷烟营销网建信息化项目建设合同\n"
            "甲方：甘肃省烟草公司兰州市公司\n"
            "乙方：浪潮软件股份有限公司\n"
        )
        fields = _mock_parse_fields(text, "test-195.8万.pdf")
        assert not is_bad_title(fields["title"])
        assert "项目建设合同" in fields["title"]


class TestParseConfidence:
    def test_high_ocr_confidence_not_capped_at_65(self) -> None:
        fields = {
            "title": "甘肃省烟草公司项目建设合同",
            "party_a": "甲方公司",
            "party_b": "乙方公司",
            "party_parse_warning": False,
        }
        meta = {
            "ocr_page_meta": [
                {"avg_confidence": 0.88, "needs_review": False},
                {"avg_confidence": 0.82, "needs_review": False},
            ],
            "ocr_needs_review": False,
        }
        conf = _compute_parse_confidence(
            fields,
            text="正文",
            ocr_used=True,
            extracted_metadata=meta,
        )
        assert conf > 0.7

    def test_low_ocr_needs_review_below_60(self) -> None:
        fields = {
            "title": "项目建设合同",
            "party_a": "A",
            "party_b": "B",
            "party_parse_warning": False,
        }
        meta = {
            "ocr_page_meta": [{"avg_confidence": 0.45, "needs_review": True}],
            "ocr_needs_review": True,
        }
        conf = _compute_parse_confidence(
            fields,
            text="正文",
            ocr_used=True,
            extracted_metadata=meta,
        )
        assert conf < 0.6

    def test_bad_title_lowers_confidence(self) -> None:
        fields = {
            "title": "--- 第 1 页 ---",
            "party_a": "A",
            "party_b": "B",
            "party_parse_warning": False,
        }
        meta = {
            "ocr_page_meta": [{"avg_confidence": 0.9, "needs_review": False}],
            "ocr_needs_review": False,
        }
        good_fields = dict(fields)
        good_fields["title"] = "某某项目建设合同"
        bad_conf = _compute_parse_confidence(
            fields,
            text="x",
            ocr_used=True,
            extracted_metadata=meta,
        )
        good_conf = _compute_parse_confidence(
            good_fields,
            text="x",
            ocr_used=True,
            extracted_metadata=meta,
        )
        assert good_conf > bad_conf
