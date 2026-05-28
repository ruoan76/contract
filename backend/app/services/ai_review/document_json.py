# -*- coding: utf-8 -*-
"""DocumentJSON — 合同正文结构化中间表示。"""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.ai_review.heading_utils import (
    PAGE_MARKER_RE,
    parse_line_to_blocks,
    parse_page_number,
)

BlockType = Literal["paragraph", "heading", "table", "page_marker"]


class DocumentBlock(BaseModel):
    type: BlockType = "paragraph"
    text: str = ""
    bbox: list[list[float]] | None = None
    anchor_id: str | None = None
    outline_label: str | None = None


class DocumentPage(BaseModel):
    index: int
    source: Literal["ocr", "native"] = "native"
    avg_confidence: float | None = None
    needs_review: bool = False
    llm_corrected: bool = False
    blocks: list[DocumentBlock] = Field(default_factory=list)


class DocumentJSON(BaseModel):
    version: str = "v1"
    pages: list[DocumentPage] = Field(default_factory=list)


def _looks_like_table_row(text: str) -> bool:
    if "\t" in text:
        return True
    parts = re.split(r"\s{2,}", text.strip())
    return len(parts) >= 3 and all(len(p) <= 40 for p in parts)


def _lines_to_blocks(lines: list[str], *, page_index: int) -> list[DocumentBlock]:
    blocks: list[DocumentBlock] = []
    block_seq = 0

    for line in lines:
        if not line.strip() and not blocks:
            continue

        stripped = line.strip()
        parsed_list = parse_line_to_blocks(line)

        is_heading = bool(parsed_list and parsed_list[0].block_type == "heading")
        if _looks_like_table_row(stripped) and not is_heading:
            anchor = f"p{page_index + 1}-b{block_seq}"
            block_seq += 1
            blocks.append(DocumentBlock(type="table", text=line, anchor_id=anchor))
            continue

        for parsed in parsed_list:
            btype = parsed.block_type
            if btype not in ("paragraph", "heading", "page_marker", "table"):
                btype = "paragraph"
            anchor = f"p{page_index + 1}-b{block_seq}"
            block_seq += 1
            blocks.append(
                DocumentBlock(
                    type=btype,  # type: ignore[arg-type]
                    text=parsed.text,
                    anchor_id=anchor,
                    outline_label=parsed.outline_label,
                )
            )
    return blocks


def page_text_to_blocks(page_text: str, *, page_index: int = 0) -> list[DocumentBlock]:
    if not page_text.strip():
        return []
    return _lines_to_blocks(page_text.split("\n"), page_index=page_index)


def build_document_json(
    pages: list[str],
    *,
    ocr_page_indices: list[int] | None = None,
    ocr_page_meta: list[dict[str, Any]] | None = None,
    ocr_used: bool = False,
    include_page_markers: bool | None = None,
) -> DocumentJSON:
    ocr_set = set(ocr_page_indices or [])
    meta_by_page: dict[int, dict[str, Any]] = {}
    if ocr_page_indices and ocr_page_meta:
        for idx, meta in zip(ocr_page_indices, ocr_page_meta):
            meta_by_page[idx] = meta

    use_markers = include_page_markers if include_page_markers is not None else ocr_used
    doc_pages: list[DocumentPage] = []

    for page_idx, page_text in enumerate(pages):
        source: Literal["ocr", "native"] = "ocr" if page_idx in ocr_set else "native"
        meta = meta_by_page.get(page_idx, {})
        blocks: list[DocumentBlock] = []

        if use_markers:
            marker_text = f"--- 第 {page_idx + 1} 页 ---"
            blocks.append(
                DocumentBlock(
                    type="page_marker",
                    text=marker_text,
                    anchor_id=f"p{page_idx + 1}-marker",
                    outline_label=marker_text,
                )
            )

        body_blocks = page_text_to_blocks(page_text.strip(), page_index=page_idx)
        blocks.extend(body_blocks)

        doc_pages.append(
            DocumentPage(
                index=page_idx,
                source=source,
                avg_confidence=meta.get("avg_confidence"),
                needs_review=bool(meta.get("needs_review")),
                llm_corrected=bool(meta.get("llm_corrected")),
                blocks=blocks,
            )
        )

    return DocumentJSON(version="v1", pages=doc_pages)


def render_document_text(doc: DocumentJSON | dict[str, Any]) -> str:
    if isinstance(doc, dict):
        doc = DocumentJSON.model_validate(doc)

    page_chunks: list[str] = []
    for page in doc.pages:
        lines: list[str] = []
        for block in page.blocks:
            if block.type == "page_marker":
                if lines and lines[-1] != "":
                    lines.append("")
                lines.append(block.text)
                lines.append("")
                continue
            text = block.text
            if block.type == "heading" and lines and lines[-1] != "":
                lines.append("")
            lines.append(text)
        chunk = "\n".join(lines).strip()
        if chunk:
            page_chunks.append(chunk)

    return "\n\n".join(page_chunks)


def extract_outline(doc: DocumentJSON | dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(doc, dict):
        doc = DocumentJSON.model_validate(doc)

    outline: list[dict[str, Any]] = []
    for page in doc.pages:
        for block in page.blocks:
            if block.type == "page_marker":
                num = parse_page_number(block.text) or (page.index + 1)
                outline.append(
                    {
                        "kind": "page",
                        "page": num,
                        "label": block.outline_label or block.text.strip(),
                        "anchor_id": block.anchor_id,
                        "needs_review": page.needs_review,
                        "llm_corrected": page.llm_corrected,
                    }
                )
            elif block.type == "heading":
                outline.append(
                    {
                        "kind": "heading",
                        "page": page.index + 1,
                        "label": (block.outline_label or block.text).strip()[:80],
                        "anchor_id": block.anchor_id,
                        "needs_review": page.needs_review,
                    }
                )
    return outline
