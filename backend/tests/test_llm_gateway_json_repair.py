# -*- coding: utf-8 -*-
"""LLM JSON 解析修复单元测试。"""
import pytest

from app.services.ai_review.llm_gateway import (
    _parse_json_response,
    _repair_json_string,
)


@pytest.mark.unit
class TestLLMGatewayJsonRepair:
    def test_parse_strict_valid(self):
        data = _parse_json_response('{"score": 80, "issues": []}', strict=True)
        assert data == {"score": 80, "issues": []}

    def test_parse_markdown_fence(self):
        raw = '```json\n{"dimension": "risk", "score": 60}\n```'
        data = _parse_json_response(raw, strict=False)
        assert data["dimension"] == "risk"

    def test_parse_trailing_comma_repair(self):
        raw = '{"a": 1, "b": 2,}'
        data = _parse_json_response(raw, strict=False)
        assert data == {"a": 1, "b": 2}

    def test_parse_embedded_json(self):
        raw = '说明文字前缀 {"ok": true} 后缀'
        data = _parse_json_response(raw, strict=False)
        assert data["ok"] is True

    def test_strict_raises_on_invalid(self):
        with pytest.raises(ValueError):
            _parse_json_response("not json at all", strict=True)

    def test_repair_json_string(self):
        assert _repair_json_string('{"x": 1,}') == '{"x": 1}'
