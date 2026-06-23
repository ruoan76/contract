"""合同模板变量解析与填充"""
import json
import re
from typing import Any

VAR_PATTERN = re.compile(r"\{([^{}]+)\}")


def extract_variables(content: str | None) -> list[str]:
    """从正文中提取 {变量名}，保持出现顺序且去重。"""
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in VAR_PATTERN.findall(content or ""):
        name = raw.strip()
        if name and name not in seen:
            seen.add(name)
            ordered.append(name)
    return ordered


def variables_to_json(names: list[str]) -> str:
    return json.dumps(names, ensure_ascii=False)


def variables_from_json(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x) for x in data]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def fill_template(content: str | None, values: dict[str, Any]) -> str:
    """将 values 填入模板正文。"""
    result = content or ""
    for name, value in values.items():
        if value is None:
            continue
        result = result.replace(f"{{{name}}}", str(value))
    return result


def validate_template_values(content: str | None, values: dict[str, Any]) -> list[str]:
    """校验必填变量是否已填写。"""
    errors: list[str] = []
    for var in extract_variables(content):
        val = values.get(var)
        if val is None or not str(val).strip():
            errors.append(f"缺少必填字段：{var}")
    return errors
