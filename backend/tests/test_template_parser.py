"""模板变量解析测试"""
import pytest

from app.services.template_parser import (
    extract_variables,
    fill_template,
    validate_template_values,
)


@pytest.mark.unit
class TestTemplateParser:
    def test_extract_variables_ordered_unique(self):
        content = "金额 {金额}，相对方 {相对方}，重复 {金额}"
        assert extract_variables(content) == ["金额", "相对方"]

    def test_fill_template(self):
        content = "乙方：{相对方}，金额 {金额} 元"
        filled = fill_template(content, {"相对方": "测试公司", "金额": "10000"})
        assert "测试公司" in filled
        assert "{金额}" not in filled

    def test_validate_missing(self):
        content = "甲方 {相对方} 金额 {金额}"
        errors = validate_template_values(content, {"相对方": "A"})
        assert any("金额" in e for e in errors)
