# -*- coding: utf-8 -*-
"""审查报告 PDF 生成测试。"""
import pytest

from app.services.ai_review_report_service import _build_html, _build_pdf_bytes
from app.services.ai_review.report_pdf_theme import GATE_LABELS, HEADER_TEXT


def _sample_report_data() -> dict:
    return {
        "review_id": "REV-TEST",
        "contract_id": 1,
        "contract_title": "青海烟草新零售系统采购合同",
        "contract_no": "CON-202605-0102",
        "counterparty_name": "某某供应商",
        "status": "ai_done",
        "overall_risk_level": "medium",
        "overall_risk_score": 65.0,
        "recommendation": "请关注违约金条款",
        "rule_violations": [{"rule_id": "TH-BOARD", "rule_name": "大额", "message": "195.8万"}],
        "clause_reviews": [
            {
                "clause": "9.1.3",
                "risk_level": "critical",
                "description": "逾期违约金比例过高",
                "suggestion": "建议调整",
            }
        ],
        "summary": {
            "review_completeness": "partial",
            "gates": {
                "gate_validity": {"status": "pass", "summary": "主体有效"},
                "gate_subject": {"status": "fail", "summary": "主体待核实"},
                "gate_clause": {"status": "warn", "summary": "条款需关注"},
                "gate_consistency": {"status": "pending", "summary": "—"},
                "gate_output": {"status": "pass", "summary": "输出完整"},
            },
        },
        "model_version": "test",
        "created_at": "2026-05-26T00:00:00",
    }


@pytest.mark.unit
class TestReviewReportPdf:
    def test_pdf_starts_with_header(self):
        pdf = _build_pdf_bytes(_sample_report_data())
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 1500

    def test_html_contains_chinese(self):
        html = _build_html({"review_id": "R1", "overall_risk_level": "high", "summary": {}})
        assert "审查报告" in html
        assert "合同审批平台" in html

    def test_html_cover_and_gates(self):
        html = _build_html(_sample_report_data())
        assert "青海烟草新零售系统采购合同" in html
        assert "效力" in html
        assert GATE_LABELS["gate_subject"] in html
        assert "gate-fail" in html or "gate-cell" in html

    def test_pdf_larger_with_full_data(self):
        small = len(_build_pdf_bytes({"review_id": "R", "summary": {}}))
        full = len(_build_pdf_bytes(_sample_report_data()))
        assert full > small

    def test_html_has_footer_disclaimer(self):
        html = _build_html(_sample_report_data())
        assert "不构成法律意见" in html
        assert HEADER_TEXT in html
