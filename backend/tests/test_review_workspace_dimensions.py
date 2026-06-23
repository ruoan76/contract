"""
评审工作台 ai_summary.dimension_summaries
"""
import json

import pytest

from app.services.review_service import get_review_workspace


@pytest.mark.unit
class TestReviewWorkspaceDimensions:
    async def test_workspace_includes_dimension_summaries(self, db_session, mock_data):
        from app.models.contract import AIReview
        from app.services.contract_service import create_contract

        created = await create_contract(
            title="维度摘要测试",
            contract_type="service",
            counterparty_name="测试公司",
            creator_id=1,
        )
        contract_id = created["id"]

        summary_json = json.dumps(
            {
                "dimensions": [
                    {
                        "dimension": "compliance",
                        "score": 40,
                        "summary": "合规存在重大瑕疵",
                        "status": "ok",
                    },
                    {
                        "dimension": "risk",
                        "score": 35,
                        "summary": "违约责任缺失",
                        "status": "failed",
                    },
                ]
            },
            ensure_ascii=False,
        )
        review = AIReview(
            contract_id=contract_id,
            version_id=1,
            review_id="REV-WS-DIM-001",
            overall_risk_level="high",
            overall_risk_score=70,
            review_status="ai_done",
            recommendation="【compliance】备用文本",
            summary=summary_json,
        )
        db_session.add(review)
        await db_session.commit()

        data = await get_review_workspace(db_session, contract_id)
        summaries = data["ai_summary"]["dimension_summaries"]
        assert len(summaries) == 2
        assert summaries[0]["dimension"] == "compliance"
        assert summaries[0]["summary"] == "合规存在重大瑕疵"
        assert summaries[1]["status"] == "failed"
