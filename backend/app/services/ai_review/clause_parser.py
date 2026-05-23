# -*- coding: utf-8 -*-
"""条款切分 — 基于启发式规则将长文本切分为独立条款。"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class Clause(BaseModel):
    """合同条款"""

    clause_id: str = Field(default="", description="条款唯一标识")
    title: str = Field(default="", description="条款标题")
    content: str = Field(default="", description="条款原文")
    section_type: str = Field(default="other", description="条款分类")
    risk_keywords: List[str] = Field(default_factory=list, description="风险关键词")


# ---------------------------------------------------------------------------
# 条款分类映射
# ---------------------------------------------------------------------------

_TYPE_KEYWORDS: dict[str, list[str]] = {
    "definitions": ["定义", "释义", "术语", "解释", "词语定义"],
    "rights_obligations": ["权利", "义务", "各方权利", "双方义务"],
    "financial": ["价款", "付款", "支付", "费用", "金额", "保证金", "定金", "违约金", "发票", "税收", "税率"],
    "breach": ["违约责任", "违约", "赔偿", "赔偿责任", "违约金", "损失赔偿"],
    "dispute": ["争议", "仲裁", "诉讼", "管辖", "法院", "争议解决"],
    "confidentiality": ["保密", "商业秘密", "保密义务", "保密期限"],
    "termination": ["终止", "解除", "期满", "合同终止", "合同解除", "提前终止"],
    "force_majeure": ["不可抗力", "自然灾害", "战争"],
    "intellectual_property": ["知识产权", "专利", "商标", "著作权", "版权"],
    "other": [],
}

_RISK_KEYWORDS = [
    "赔偿", "违约金", "赔偿上限", "责任限制", "免责", "不可抗力",
    "连带责任", "担保", "抵押", "质押", "解除", "终止",
    "管辖", "仲裁", "诉讼", "争议", "保密", "竞业",
    "单方", "任意", "无条件", "不可撤销",
]


def _classify_section(title: str, content: str) -> tuple[str, list[str]]:
    """根据标题和内容推断条款类型，并提取风险关键词。

    Args:
        title: 条款标题
        content: 条款正文

    Returns:
        (section_type, risk_keywords)
    """
    combined = (title + content).lower()
    found_keywords = [kw for kw in _RISK_KEYWORDS if kw in combined]

    for section_type, keywords in _TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                return section_type, found_keywords

    return "other", found_keywords


# ---------------------------------------------------------------------------
# 分块正则（适配中英文合同）
# ---------------------------------------------------------------------------

# Pattern 1: "第X条" — 中文标准条款
_RE_CHINESE = re.compile(
    r"(^\s*第[一二三四五六七八九十百千\d]+[条章节段部分]\s+.+?)",
    re.MULTILINE,
)

# Pattern 2: "Article X" / "Section X" — 英文标准条款
_RE_ENGLISH = re.compile(
    r"(^\s*(Article|Section|Clause|Part|Chapter)\s+\d+[A-Z]?\b\s*.+?)",
    re.MULTILINE | re.IGNORECASE,
)

# Pattern 3: "§X" / "§ X" — 符号条款
_RE_SYMBOL = re.compile(
    r"(^\s*§\s*\d+\s*.+?)",
    re.MULTILINE,
)

# Pattern 4: "X." — 数字序号条款 (如 "1. 合同标的")
_RE_NUMBERED = re.compile(
    r"(^\s*\d+\.\s+\S.+?)",
    re.MULTILINE,
)

_ALL_PATTERNS: list[re.Pattern] = [
    _RE_CHINESE,
    _RE_ENGLISH,
    _RE_SYMBOL,
    _RE_NUMBERED,
]


def _split_into_blocks(text: str) -> list[tuple[str, str]]:
    """将文本按条款标记切分，返回 [(title, content), ...]。

    策略：尝试多种正则模式，选取匹配数最多的一个。

    Args:
        text: 完整合同文本

    Returns:
        条款列表，每项为 (标题, 正文) 元组
    """
    best_pattern: Optional[re.Pattern] = None
    best_matches = 0

    for pattern in _ALL_PATTERNS:
        matches = list(pattern.finditer(text))
        if len(matches) > best_matches:
            best_matches = len(matches)
            best_pattern = pattern

    if best_pattern is None or best_matches < 2:
        logger.warning(
            "未找到明确的条款分隔符，将整份合同作为单一条款处理"
        )
        return [("合同全文", text)]

    # 按匹配位置拆分
    blocks: list[tuple[str, str]] = []
    positions = [(m.start(), m.group(1).strip()) for m in best_pattern.finditer(text)]

    for idx, (start_pos, title) in enumerate(positions):
        end_pos = positions[idx + 1][0] if idx + 1 < len(positions) else len(text)
        content = text[start_pos:end_pos].strip()
        if content:
            blocks.append((title, content))

    return blocks


async def parse_clauses(
    full_text: str,
    *,
    contract_type: Optional[str] = None,
) -> List[Clause]:
    """将长文本切分为独立条款。

    Args:
        full_text: 完整合同文本
        contract_type: 合同类型（可选，用于后续分类增强）

    Returns:
        Clause 对象列表
    """
    if not full_text or not full_text.strip():
        logger.warning("输入文本为空，返回空条款列表")
        return []

    blocks = _split_into_blocks(full_text)
    clauses: list[Clause] = []

    for idx, (title, content) in enumerate(blocks, start=1):
        section_type, risk_keywords = _classify_section(title, content)
        clauses.append(
            Clause(
                clause_id=f"CLS-{idx:03d}",
                title=title[:100],  # 截断过长标题
                content=content,
                section_type=section_type,
                risk_keywords=risk_keywords,
            )
        )

    logger.info("切分完成: 共 %d 个条款", len(clauses))
    return clauses
