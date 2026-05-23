"""
AI Review Engine Tests
测试 AI审查引擎（mock LLM 调用）
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

# ==============================================================================
# AI Review Engine Tests
# ==============================================================================

@pytest.mark.unit
class TestAIReviewEngine:
    """AIReviewEngine 测试"""
    
    async def test_engine_initialization(self, mock_data):
        """测试引擎初始化"""
        from app.services.ai_review.ai_engine import AIReviewEngine
        
        engine = AIReviewEngine()
        
        assert engine is not None
        assert hasattr(engine, "_client")
    
    async def test_review_contract_success(self, mock_openai_client, mock_data):
        """测试成功审查合同"""
        from app.services.ai_review.ai_engine import AIReviewEngine
        from app.services.ai_review.clause_parser import Clause
        
        engine = AIReviewEngine()
        
        clauses = [
            Clause(
                clause_id="1",
                title="付款条款",
                content="甲方应在合同签订后 7 天内支付全款",
                section_type="financial",
            ),
        ]
        
        result = await engine.review(
            full_text="合同内容...",
            clauses=clauses,
            contract_type="service",
        )
        
        assert result is not None
        assert hasattr(result, "overall_risk_score")
        assert hasattr(result, "clause_reviews")
        assert hasattr(result, "dimension_scores")
    
    async def test_review_contract_empty_text(self, mock_openai_client, mock_data):
        """测试空文本审查"""
        from app.services.ai_review.ai_engine import AIReviewEngine
        
        engine = AIReviewEngine()
        
        result = await engine.review(
            full_text="",
            clauses=[],
            contract_type="service",
        )
        
        assert result is not None
        assert result.overall_risk_score >= 0
    
    async def test_review_contract_timeout_handling(self, mock_data):
        """测试超时处理"""
        from app.services.ai_review.ai_engine import AIReviewEngine
        from app.services.ai_review.clause_parser import Clause
        import openai
        
        engine = AIReviewEngine()
        
        # Mock client to raise timeout
        with patch.object(engine._client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = openai.APITimeoutError("Timeout")
            
            clauses = [Clause(clause_id="1", title="Test", content="Content", section_type="other")]
            
            result = await engine.review(
                full_text="Test content",
                clauses=clauses,
                contract_type="service",
            )
            
            # 应该返回默认评分
            assert result.overall_risk_score >= 0
    
    async def test_review_contract_api_error_handling(self, mock_data):
        """测试 API 错误处理"""
        from app.services.ai_review.ai_engine import AIReviewEngine
        from app.services.ai_review.clause_parser import Clause
        import openai
        
        engine = AIReviewEngine()
        
        with patch.object(engine._client.chat.completions, 'create') as mock_create:
            mock_create.side_effect = openai.APIStatusError("Service unavailable", response=MagicMock(), body={})
            
            clauses = [Clause(clause_id="1", title="Test", content="Content", section_type="other")]
            
            result = await engine.review(
                full_text="Test content",
                clauses=clauses,
                contract_type="service",
            )
            
            # 应该返回默认评分
            assert result.overall_risk_score >= 0


@pytest.mark.unit
class TestDimensionReview:
    """单维度审查测试"""
    
    async def test_review_one_dimension(self, mock_openai_client, mock_data):
        """测试单维度审查"""
        from app.services.ai_review.ai_engine import AIReviewEngine, DimensionRequest
        
        engine = AIReviewEngine()
        
        request = DimensionRequest(
            contract_text="合同全文",
            clauses=[],
            contract_type="service",
            dimension="compliance",
            checklist=[],
            risk_labels=[],
        )
        
        result = await engine._review_one_dimension(request)
        
        assert result is not None
        assert hasattr(result, "dimension")
        assert hasattr(result, "score")


@pytest.mark.unit
class TestClauseReview:
    """条款审查测试"""
    
    async def test_generate_clause_reviews(self, mock_data):
        """测试条款审查生成"""
        from app.services.ai_review.ai_engine import AIReviewEngine, Clause, DimensionScore, Issue
        
        engine = AIReviewEngine()
        
        clauses = [
            Clause(
                clause_id="1",
                title="违约责任",
                content="任何一方违约需支付合同金额 20% 的违约金",
                section_type="breach",
                risk_keywords=["违约金", "赔偿"],
            ),
        ]
        
        dimension_results = [
            DimensionScore(
                dimension="risk",
                score=65.0,
                issues=[
                    Issue(keyword="违约金", severity="medium", description="违约金比例较高"),
                ],
                summary="风险条款需注意",
            ),
        ]
        
        clause_reviews = engine._generate_clause_reviews(clauses, dimension_results)
        
        assert len(clause_reviews) == 1
        assert clause_reviews[0].clause_id == "1"
        assert clause_reviews[0].risk_level in ("low", "medium", "high", "critical")


@pytest.mark.unit
class TestRiskScoring:
    """风险评分测试"""
    
    def test_compute_clause_risk_score(self, mock_data):
        """测试条款风险评分计算"""
        from app.services.ai_review.ai_engine import AIReviewEngine, Issue
        
        engine = AIReviewEngine()
        
        # 无问题
        issues = []
        score = engine._compute_clause_risk_score(issues)
        assert score == 0.0
        
        # 低风险
        issues = [Issue(keyword="test", severity="low", description="Test")]
        score = engine._compute_clause_risk_score(issues)
        assert score == 10.0
        
        # 中风险
        issues = [Issue(keyword="test", severity="medium", description="Test")]
        score = engine._compute_clause_risk_score(issues)
        assert score == 30.0
        
        # 高风险
        issues = [Issue(keyword="test", severity="high", description="Test")]
        score = engine._compute_clause_risk_score(issues)
        assert score == 60.0
        
        # 严重风险
        issues = [Issue(keyword="test", severity="critical", description="Test")]
        score = engine._compute_clause_risk_score(issues)
        assert score == 90.0
        
        # 多个问题取最大
        issues = [
            Issue(keyword="test1", severity="low", description="Test1"),
            Issue(keyword="test2", severity="high", description="Test2"),
        ]
        score = engine._compute_clause_risk_score(issues)
        assert score == 60.0


@pytest.mark.unit
class TestGetEngine:
    """get_engine 单例测试"""
    
    def test_get_engine_singleton(self, mock_data):
        """测试 get_engine 返回单例"""
        from app.services.ai_review.ai_engine import get_engine, _engine
        
        # 清除缓存
        _engine = None
        
        engine1 = get_engine()
        engine2 = get_engine()
        
        assert engine1 is engine2


@pytest.mark.unit
class TestReviewContract快捷函数:
    """review_contract 快捷函数测试"""
    
    async def test_review_contract_function(self, mock_openai_client, mock_data):
        """测试 review_contract 快捷函数"""
        from app.services.ai_review.ai_engine import review_contract
        from app.services.ai_review.clause_parser import Clause
        
        clauses = [Clause(clause_id="1", title="Test", content="Content", section_type="other")]
        
        result = await review_contract(
            contract_text="合同内容",
            clauses=clauses,
            contract_type="service",
        )
        
        assert result is not None
        assert hasattr(result, "overall_risk_score")
