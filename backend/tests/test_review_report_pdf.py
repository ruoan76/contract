# -*- coding: utf-8 -*-
"""审查报告 PDF 生成测试。"""
import pytest

from app.services.ai_review_report_service import _build_pdf_bytes, _build_html


@pytest.mark.unit
class TestReviewReportPdf:
    def test_pdf_starts_with_header(self):
        data = {
            "review_id": "REV-TEST",
            "contract_id": 1,
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
            "summary": {"review_completeness": "partial", "gates": {}},
            "model_version": "test",
            "created_at": "2026-05-26T00:00:00",
        }
        pdf = _build_pdf_bytes(data)
        assert pdf.startswith(b"%PDF")
        assert len(pdf) > 500

    def test_html_contains_chinese(self):
        html = _build_html({"review_id": "R1", "overall_risk_level": "high", "summary": {}})
        assert "审查报告" in html
