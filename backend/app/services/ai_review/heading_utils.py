# -*- coding: utf-8 -*-
"""合同正文标题识别 — 条款/章节/分页。"""
from __future__ import annotations

import re
from dataclasses import dataclass

PAGE_MARKER_RE = re.compile(r"^---\s*第\s*(\d+)\s*页\s*---$")
CLAUSE_HEADING_RE = re.compile(r"^(第[一二三四五六七八九十百零〇两]+条)")
NUMBERED_SECTION_RE = re.compile(r"^(\d+(?:\.\d+){0,4})\s+(.+)$")
# OCR 段落空行：条款或数字章节行首
HEADING_LINE_START_RE = re.compile(
    r"^(?:第[一二三四五六七八九十百零〇两]+条|\d+(?:\.\d+){0,4}\s+)"
)

# 目录短标题最大长度
HEADING_LABEL_MAX = 80
HEADING_TITLE_SEGMENT_MAX = 36
HEADING_LINE_MAX = 80


@dataclass(frozen=True)
class ParsedLine:
    block_type: str  # paragraph | heading | page_marker | table
    text: str
    outline_label: str | None = None


def is_page_marker(line: str) -> bool:
    return bool(PAGE_MARKER_RE.match(line.strip()))


def is_heading_line_start(line: str) -> bool:
    return bool(HEADING_LINE_START_RE.match(line.strip()))


def parse_page_number(line: str) -> int | None:
    m = PAGE_MARKER_RE.match(line.strip())
    return int(m.group(1)) if m else None


def split_mixed_heading_line(line: str) -> tuple[str, str] | None:
    """
    拆分「编号 + 标题 + 正文」混合行。
    返回 (heading_text, remainder) 或 None（非可拆分标题）。
    """
    stripped = line.strip()
    if not stripped:
        return None

    if CLAUSE_HEADING_RE.match(stripped):
        if len(stripped) <= HEADING_LINE_MAX:
            return stripped, ""
        # 条款行过长：取前段为标题
        return stripped[:HEADING_LINE_MAX], stripped[HEADING_LINE_MAX:].strip()

    m = NUMBERED_SECTION_RE.match(stripped)
    if not m:
        return None

    number, rest = m.group(1), m.group(2).strip()
    if len(stripped) <= HEADING_LINE_MAX and len(rest) <= HEADING_TITLE_SEGMENT_MAX:
        return stripped, ""

    # 尝试在 rest 中找标题/正文分界：括号段落后、或第二个句号前
    title_part = rest
    body_part = ""

    paren_num = re.search(r"\(\d+\)\s*", rest)
    if paren_num:
        cut = paren_num.end()
        candidate_title = rest[:cut].strip()
        if len(candidate_title) <= HEADING_TITLE_SEGMENT_MAX:
            title_part = candidate_title
            body_part = rest[cut:].strip()
    elif len(rest) > HEADING_TITLE_SEGMENT_MAX:
        # 取前 36 字为标题，其余为正文
        title_part = rest[:HEADING_TITLE_SEGMENT_MAX].rstrip()
        body_part = rest[HEADING_TITLE_SEGMENT_MAX:].strip()

    heading_text = f"{number} {title_part}".strip()
    if len(heading_text) > HEADING_LABEL_MAX:
        heading_text = heading_text[:HEADING_LABEL_MAX]

    if body_part:
        return heading_text, body_part
    if len(stripped) <= HEADING_LINE_MAX:
        return stripped, ""
    return heading_text, ""


def parse_line_to_blocks(line: str) -> list[ParsedLine]:
    """将单行解析为一个或多个块。"""
    stripped = line.strip()
    if not stripped:
        return []

    if is_page_marker(stripped):
        return [ParsedLine(block_type="page_marker", text=stripped, outline_label=stripped)]

    split = split_mixed_heading_line(stripped)
    if split:
        heading_text, remainder = split
        blocks = [
            ParsedLine(
                block_type="heading",
                text=heading_text,
                outline_label=heading_text[:HEADING_LABEL_MAX],
            )
        ]
        if remainder:
            blocks.append(ParsedLine(block_type="paragraph", text=remainder))
        return blocks

    return [ParsedLine(block_type="paragraph", text=line)]


def outline_label_for_text(text: str, block_type: str) -> str | None:
    if block_type == "page_marker":
        return text.strip()
    if block_type == "heading":
        split = split_mixed_heading_line(text.strip())
        if split:
            return split[0][:HEADING_LABEL_MAX]
        return text.strip()[:HEADING_LABEL_MAX]
    return None
