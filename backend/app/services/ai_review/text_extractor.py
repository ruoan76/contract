# -*- coding: utf-8 -*-
"""合同文本提取 — 支持 PDF / DOCX / TXT"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, List, Optional

import fitz  # PyMuPDF
from docx import Document as DocxDocument
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据模型
# ---------------------------------------------------------------------------

class ExtractedText(BaseModel):
    """提取后的合同文本"""

    full_text: str = Field(default="", description="完整纯文本")
    pages: List[str] = Field(default_factory=list, description="每页文本列表")
    tables: List[List[List[str]]] = Field(default_factory=list, description="表格数据")
    metadata: dict[str, Any] = Field(default_factory=dict, description="文件元数据")


# ---------------------------------------------------------------------------
# 公共入口
# ---------------------------------------------------------------------------

async def extract_text(file_path: str, file_type: str) -> ExtractedText:
    """从合同文件中提取文本

    Args:
        file_path: 文件绝对路径
        file_type: 文件类型 (pdf / docx / txt)

    Returns:
        ExtractedText 包含提取结果

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 不支持的文件类型或文件过大
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    file_size = path.stat().st_size
    if file_size > settings.MAX_FILE_SIZE:
        raise ValueError(
            f"文件大小 {file_size} 字节超过限制 {settings.MAX_FILE_SIZE}"
        )

    file_type = file_type.lower().lstrip(".")

    extractor = _ROUTING.get(file_type)
    if extractor is None:
        raise ValueError(f"不支持的文件类型: {file_type}")

    return await extractor(path, file_type)


# ---------------------------------------------------------------------------
# PDF 提取
# ---------------------------------------------------------------------------

async def _extract_pdf(path: Path, file_type: str) -> ExtractedText:
    """使用 PyMuPDF 提取 PDF 文本"""
    loop = asyncio.get_event_loop()
    pages: list[str] = []
    tables: list[list[list[str]]] = []
    full_parts: list[str] = []

    def _read() -> tuple[list[str], list[list[list[str]]], dict[str, Any]]:
        doc = fitz.open(str(path))
        try:
            metadata = dict(doc.metadata or {})
            page_texts: list[str] = []
            all_tables: list[list[list[str]]] = []

            for page_idx in range(len(doc)):
                page = doc[page_idx]
                text = page.get_text()
                page_texts.append(text)

            return page_texts, all_tables, metadata
        finally:
            doc.close()

    pages, tables, metadata = await loop.run_in_executor(None, _read)

    full_text = "\n".join(pages)

    return ExtractedText(
        full_text=full_text,
        pages=pages,
        tables=tables,
        metadata={
            "file_type": file_type,
            "page_count": len(pages),
            "source_metadata": metadata,
        },
    )


# ---------------------------------------------------------------------------
# DOCX 提取
# ---------------------------------------------------------------------------

async def _extract_docx(path: Path, file_type: str) -> ExtractedText:
    """使用 python-docx 提取 DOCX 文本"""
    loop = asyncio.get_event_loop()

    def _read() -> tuple[str, list[str], list[list[list[str]]]]:
        doc = DocxDocument(str(path))

        paragraphs: list[str] = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text)

        tables: list[list[list[str]]] = []
        for table in doc.tables:
            table_data: list[list[str]] = []
            for row in table.rows:
                row_data: list[str] = []
                for cell in row.cells:
                    row_data.append(cell.text.strip())
                table_data.append(row_data)
            if table_data:
                tables.append(table_data)

        full_text = "\n".join(paragraphs)
        return full_text, paragraphs, tables

    full_text, paragraphs, tables = await loop.run_in_executor(None, _read)

    return ExtractedText(
        full_text=full_text,
        pages=paragraphs,
        tables=tables,
        metadata={"file_type": file_type, "para_count": len(paragraphs)},
    )


# ---------------------------------------------------------------------------
# TXT 提取
# ---------------------------------------------------------------------------

async def _extract_txt(path: Path, file_type: str) -> ExtractedText:
    """提取纯文本文件（自动处理编码）"""
    loop = asyncio.get_event_loop()

    def _read() -> str:
        for encoding in ("utf-8", "gbk", "gb2312", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except (UnicodeDecodeError, ValueError):
                continue
        return path.read_text(encoding="utf-8", errors="replace")

    text = await loop.run_in_executor(None, _read)
    lines = text.splitlines()

    return ExtractedText(
        full_text=text,
        pages=lines,
        tables=[],
        metadata={"file_type": file_type, "line_count": len(lines)},
    )


# ---------------------------------------------------------------------------
# 路由表
# ---------------------------------------------------------------------------

_ROUTING: dict[str, Any] = {
    "pdf": _extract_pdf,
    "docx": _extract_docx,
    "txt": _extract_txt,
}
