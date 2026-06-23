# -*- coding: utf-8 -*-
"""OCR 文本质量辅助 — 乱码率、逐页 OCR 判定。"""
from __future__ import annotations

import re

# 合同常见合法字符（中文、数字、标点、空白）
_VALID_CHAR_RE = re.compile(
    r"[\u4e00-\u9fff\w\s\d"
    r"，。、；：""''（）【】《》·—－\-_\.\,\:\;\(\)\[\]\/\\%￥¥&@#]"
)


def gibberish_ratio(text: str) -> float:
    """
    乱码率：非合法字符占比。越高表示越像 OCR 噪声或劣质文字层。
    空文本返回 0.0。
    """
    stripped = text.strip()
    if not stripped:
        return 0.0
    valid = sum(1 for ch in stripped if _VALID_CHAR_RE.match(ch))
    return 1.0 - (valid / len(stripped))


def page_needs_ocr(
    text: str,
    *,
    min_chars: int,
    gibberish_threshold: float,
) -> bool:
    """判断单页是否应走 OCR（字数过少或乱码率过高）。"""
    stripped = text.strip()
    if len(stripped) < min_chars:
        return True
    return gibberish_ratio(stripped) > gibberish_threshold


def is_pdf_binary_text(text: str) -> bool:
    """
    判断文本是否实为 PDF 二进制被误解码（%PDF 头、obj 流等）。
    用于拦截 extract 失败后的危险回退结果。
    """
    if not text or len(text) < 8:
        return False
    sample = text[:4096]
    if sample.lstrip().startswith("%PDF-"):
        return True
    markers = ("endobj", "/Type", "/Catalog", "/Pages", "stream", "xref")
    hits = sum(1 for m in markers if m in sample)
    if hits >= 3 and sample.count("<<") >= 2:
        return True
    return False


def indices_needing_ocr(
    pages: list[str],
    *,
    min_chars: int,
    gibberish_threshold: float,
) -> list[int]:
    """返回需要 OCR 的页索引列表。"""
    return [
        idx
        for idx, page in enumerate(pages)
        if page_needs_ocr(
            page,
            min_chars=min_chars,
            gibberish_threshold=gibberish_threshold,
        )
    ]
