# -*- coding: utf-8 -*-
"""DocumentJSON 构建与渲染单测。"""
from __future__ import annotations

from app.services.ai_review.document_json import (
    build_document_json,
    extract_outline,
    render_document_text,
)
from app.services.ai_review.heading_utils import split_mixed_heading_line


def test_build_document_json_uses_layout_lines_bbox() -> None:
    pages = ["ignored when layout_lines present"]
    doc = build_document_json(
        pages,
        ocr_page_indices=[0],
        ocr_page_meta=[
            {
                "layout_lines": [
                    {"text": "第一条 总则", "bbox": [[0, 0], [10, 0], [10, 5], [0, 5]]},
                ],
                "layout_suspect": True,
            }
        ],
        ocr_used=True,
    )
    assert doc.pages[0].layout_suspect is True
    para = next(b for b in doc.pages[0].blocks if b.type != "page_marker")
    assert para.bbox is not None
    assert "第一条" in para.text


def test_build_document_json_with_page_markers() -> None:
    pages = ["第一条 总则\n本合同由双方签订。", "第二条 付款"]
    doc = build_document_json(
        pages,
        ocr_page_indices=[0, 1],
        ocr_page_meta=[
            {"avg_confidence": 0.9, "needs_review": False},
            {"avg_confidence": 0.4, "needs_review": True},
        ],
        ocr_used=True,
    )
    assert len(doc.pages) == 2
    assert doc.pages[0].blocks[0].type == "page_marker"
    assert doc.pages[0].blocks[0].anchor_id == "p1-marker"
    assert doc.pages[1].needs_review is True
    text = render_document_text(doc)
    assert "--- 第 1 页 ---" in text
    assert "第一条" in text


def test_render_heading_paragraph_spacing() -> None:
    pages = ["第一条 总则\n正文内容"]
    doc = build_document_json(pages, ocr_used=True)
    rendered = render_document_text(doc)
    assert "第一条" in rendered
    assert "正文内容" in rendered


def test_extract_outline() -> None:
    pages = ["第一条 总则", "第二条 付款"]
    doc = build_document_json(pages, ocr_used=True)
    outline = extract_outline(doc)
    kinds = {item["kind"] for item in outline}
    assert "page" in kinds
    assert "heading" in kinds
    heading_items = [i for i in outline if i["kind"] == "heading"]
    assert all(i.get("anchor_id") for i in heading_items)


def test_short_numbered_heading() -> None:
    pages = ["2.2.3 系统开发"]
    doc = build_document_json(pages, ocr_used=True)
    headings = [
        b for p in doc.pages for b in p.blocks if b.type == "heading"
    ]
    assert len(headings) == 1
    assert headings[0].text == "2.2.3 系统开发"
    assert headings[0].outline_label == "2.2.3 系统开发"
    assert headings[0].anchor_id is not None


def test_long_mixed_heading_splits() -> None:
    long_line = (
        "2.2.3 系统开发 (5) 系统开发完成前，甲方应提供必要的技术文档"
        "与接口说明，乙方据此开展开发工作。"
    )
    split = split_mixed_heading_line(long_line)
    assert split is not None
    heading_text, body = split
    assert heading_text.startswith("2.2.3")
    assert len(heading_text) <= 80
    assert "系统开发完成前" in body

    doc = build_document_json([long_line], ocr_used=True)
    types = [b.type for p in doc.pages for b in p.blocks if b.type != "page_marker"]
    assert "heading" in types
    assert "paragraph" in types
    outline = extract_outline(doc)
    heading_outline = [i for i in outline if i["kind"] == "heading"][0]
    assert "系统开发完成前" not in heading_outline["label"]


def test_outline_has_anchor_ids() -> None:
    pages = ["2.2.2 系统设计\n2.2.3 系统开发"]
    doc = build_document_json(pages, ocr_used=True)
    outline = extract_outline(doc)
    for item in outline:
        assert item.get("anchor_id"), f"missing anchor_id on {item}"


def test_native_without_markers() -> None:
    pages = ["甲方：测试公司\n乙方：乙公司"]
    doc = build_document_json(pages, ocr_used=False)
    text = render_document_text(doc)
    assert "--- 第" not in text
    assert "甲方" in text
