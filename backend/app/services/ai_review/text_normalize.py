# -*- coding: utf-8 -*-
"""合同正文轻量规范化 — OCR 与原生提取均可使用。"""
from __future__ import annotations

import re

# 常见半角标点 → 全角（合同场景）
_PUNCT_MAP = str.maketrans({
    ",": "，",
    ";": "；",
    ":": "：",
    "(": "（",
    ")": "）",
    "[": "【",
    "]": "】",
})

# 中文与 ASCII 字母数字之间的多余空格
_CJK_ASCII_SPACE_RE = re.compile(
    r"([\u4e00-\u9fff])\s+([A-Za-z0-9])|([A-Za-z0-9])\s+([\u4e00-\u9fff])"
)
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def normalize_contract_text(text: str) -> str:
    """折叠空白、统一标点、清理中英文间多余空格。"""
    if not text:
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.translate(_PUNCT_MAP)
    normalized = _CJK_ASCII_SPACE_RE.sub(r"\1\2\3\4", normalized)

    lines: list[str] = []
    for line in normalized.split("\n"):
        stripped = _MULTI_SPACE_RE.sub(" ", line.strip())
        lines.append(stripped)
    normalized = "\n".join(lines)
    normalized = _BLANK_LINES_RE.sub("\n\n", normalized)
    return normalized.strip()
