"""合同文件解析 — 文本提取 + 字段识别（支持 mock / LLM）"""
from __future__ import annotations

import logging
import os
import re
import tempfile
from typing import Any, Optional

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.ai_review.heading_utils import is_bad_title, is_page_marker
from app.services.ai_review.ocr_text_utils import is_pdf_binary_text
from app.services.ai_review.text_extractor import extract_text
from app.services.ai_review.text_normalize import normalize_contract_text

logger = logging.getLogger(__name__)
from app.services.ai_review.ocr_postprocess import enrich_fields_with_dictionary
from app.services.parse_llm_service import (
    detect_party_parse_warning,
    extract_fields_with_llm,
    fuzzy_match_counterparty_names,
)


def _guess_file_type(filename: str, content_type: Optional[str]) -> str:
    ext = os.path.splitext(filename or "")[1].lower().lstrip(".")
    if ext in ("pdf", "docx", "txt", "doc"):
        return "docx" if ext == "doc" else ext
    if content_type:
        if "pdf" in content_type:
            return "pdf"
        if "word" in content_type or "docx" in content_type:
            return "docx"
        if "text" in content_type:
            return "txt"
    return ext or "txt"


_TITLE_CONTRACT_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9（）()·\-—]{4,80}合同")
_PARTY_LINE_RE = re.compile(r"^[甲乙丙丁]方[：:]")


def _title_from_filename(filename: str) -> str:
    base = os.path.splitext(filename or "")[0].strip()
    if not base:
        return "未命名合同"
    base = re.sub(r"[-—]\s*[\d.]+\s*万(?:元)?\s*$", "", base).strip()
    return base[:120] or "未命名合同"


def _is_skip_title_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) < 4:
        return True
    if is_page_marker(stripped):
        return True
    if _PARTY_LINE_RE.match(stripped):
        return True
    if re.fullmatch(r"[\s\-—_=*#·.]+", stripped):
        return True
    return False


def extract_contract_title(text: str, filename: str) -> tuple[str, str]:
    """
    从正文/文件名推断合同标题。
    返回 (title, title_source)，source 为 body | filename | default。
    """
    snippet = (text or "")[:3000]
    lines = snippet.splitlines()[:30]

    for line in lines:
        stripped = line.strip()
        if _is_skip_title_line(stripped):
            continue
        if "合同" in stripped and 6 <= len(stripped) <= 120:
            return stripped[:120], "body"

    match = _TITLE_CONTRACT_RE.search(snippet)
    if match:
        return match.group(0)[:120], "body"

    for line in lines:
        stripped = line.strip()
        if _is_skip_title_line(stripped):
            continue
        return stripped[:120], "body"

    fn_title = _title_from_filename(filename)
    if fn_title != "未命名合同":
        return fn_title, "filename"
    return "未命名合同", "default"


def _ensure_valid_title(
    fields: dict[str, Any],
    text: str,
    filename: str,
) -> dict[str, Any]:
    """LLM/正则标题若为分页标记等无效值，则重新抽取。"""
    title = fields.get("title")
    if is_bad_title(title):
        new_title, source = extract_contract_title(text, filename)
        fields["title"] = new_title
        fields["title_source"] = source
    elif not fields.get("title_source"):
        fields["title_source"] = "llm" if fields.get("parse_source") == "llm" else "body"
    return fields


def _compute_parse_confidence(
    fields: dict[str, Any],
    *,
    text: str,
    ocr_used: bool,
    extracted_metadata: dict[str, Any],
) -> float:
    if not text.strip():
        return 0.2

    field_score = 1.0
    if is_bad_title(fields.get("title")):
        field_score -= 0.15
    if fields.get("party_parse_warning"):
        field_score -= 0.2
    if not fields.get("party_a") and not fields.get("party_b"):
        field_score -= 0.1
    field_score = max(0.0, min(1.0, field_score))

    if ocr_used:
        meta_list = extracted_metadata.get("ocr_page_meta") or []
        confs = [
            float(m["avg_confidence"])
            for m in meta_list
            if m.get("avg_confidence") is not None
        ]
        if confs:
            ocr_avg = sum(confs) / len(confs)
            confidence = min(0.92, max(0.35, ocr_avg * 0.85 + field_score * 0.15))
        else:
            confidence = 0.75 * field_score
        if extracted_metadata.get("ocr_needs_review"):
            confidence = min(confidence, 0.55)
            fields["ocr_needs_review"] = True
        if extracted_metadata.get("layout_suspect"):
            confidence = min(confidence, 0.55)
            fields["layout_suspect"] = True
    else:
        confidence = 0.75 * field_score

    if fields.get("party_parse_warning"):
        confidence = min(confidence, 0.55)

    return round(confidence, 4)


def _mock_parse_fields(text: str, filename: str) -> dict[str, Any]:
    """基于正则的 mock 字段提取。"""
    amount_match = re.search(
        r"(?:金额|总价|合同金额|人民币)\s*[：:￥]?\s*([\d,]+(?:\.\d+)?)\s*(?:元|万元)?",
        text,
    )
    amount = None
    if amount_match:
        raw = amount_match.group(1).replace(",", "")
        try:
            amount = float(raw)
            if "万元" in amount_match.group(0):
                amount *= 10000
        except ValueError:
            amount = None

    party_a = None
    party_b = None
    party_match = re.search(r"甲方[：:]\s*(.+?)[\n\r]", text)
    if party_match:
        party_a = party_match.group(1).strip()[:100]
    party_match = re.search(r"乙方[：:]\s*(.+?)[\n\r]", text)
    if party_match:
        party_b = party_match.group(1).strip()[:100]

    title, title_source = extract_contract_title(text, filename)

    # 文件名中的「195.8万」等金额提示（扫描件 OCR 前常用）
    amount_source = "body"
    fn_amount: float | None = None
    fn_amt = re.search(r"([\d.]+)\s*万", filename)
    if fn_amt:
        try:
            fn_amount = float(fn_amt.group(1)) * 10000
        except ValueError:
            fn_amount = None

    party_parse_warning = detect_party_parse_warning(party_a, party_b)

    if amount is None and fn_amount is not None:
        amount = fn_amount
        amount_source = "filename"
    elif amount is not None and fn_amount is not None and abs(amount - fn_amount) > 1:
        amount = fn_amount
        amount_source = "filename_override"

    return {
        "title": title,
        "title_source": title_source,
        "party_a": party_a,
        "party_b": party_b,
        "amount": amount,
        "amount_source": amount_source,
        "party_parse_warning": party_parse_warning,
        "currency": "CNY",
        "contract_type": "service" if "服务" in text else "purchase",
        "start_date": None,
        "end_date": None,
        "confidence": 0.75 if text.strip() else 0.3,
        "mock": True,
        "parse_source": "regex",
    }


def _merge_llm_fields(
    base: dict[str, Any],
    llm: dict[str, Any],
) -> dict[str, Any]:
    """LLM 字段覆盖正则结果（非空时）。"""
    merged = dict(base)
    merged["mock"] = False
    merged["parse_source"] = "llm"
    for key in ("title", "party_a", "party_b", "amount", "contract_type", "confidence"):
        val = llm.get(key)
        if val is not None and val != "":
            merged[key] = val
    if llm.get("confidence") is not None:
        merged["confidence"] = llm["confidence"]
    merged["party_parse_warning"] = detect_party_parse_warning(
        merged.get("party_a"),
        merged.get("party_b"),
    )
    if merged["party_parse_warning"]:
        merged["confidence"] = min(float(merged.get("confidence") or 0.75), 0.55)
    return merged


def _decode_plaintext_fallback(content: bytes) -> str:
    """仅用于 txt 等纯文本：按常见编码尝试解码。"""
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


async def extract_bytes_to_text(
    content: bytes,
    filename: str,
    content_type: Optional[str] = None,
) -> tuple[str, dict[str, Any]]:
    """从上传字节提取正文（含 PDF OCR 回退）。"""
    file_type = _guess_file_type(filename, content_type)
    suffix = f".{file_type}" if file_type else ""

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    extracted_metadata: dict[str, Any] = {}
    text = ""
    text_raw = ""
    try:
        extracted = await extract_text(tmp_path, file_type)
        text_raw = extracted.full_text or ""
        text = normalize_contract_text(text_raw)
        extracted_metadata = extracted.metadata or {}
    except Exception as exc:
        logger.exception("合同文件文本提取失败: %s (%s)", filename, file_type)
        if file_type in ("pdf", "docx", "doc"):
            raise ValueError(
                "PDF/Word 文本提取失败，请确认 OCR 依赖已安装且文件未损坏"
            ) from exc
        text_raw = _decode_plaintext_fallback(content)
        text = normalize_contract_text(text_raw)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if is_pdf_binary_text(text):
        raise ValueError(
            "解析结果疑似 PDF 原始数据而非合同正文，请检查 OCR 环境或重新上传"
        )

    max_chars = settings.CONTRACT_CONTENT_MAX_CHARS
    if len(text) > max_chars:
        text = text[:max_chars]
    return text, extracted_metadata


async def parse_contract_file(
    file: UploadFile,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    上传合同文件，提取文本并返回解析字段。

    AI_PARSE_MOCK=1（默认）时使用启发式正则；AI_PARSE_MOCK=0 时尝试 LLM 结构化提取。
    """
    filename = file.filename or "upload.txt"
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise ValueError(f"文件超过大小限制 {settings.MAX_FILE_SIZE} 字节")

    file_type = _guess_file_type(filename, file.content_type)
    text, extracted_metadata = await extract_bytes_to_text(
        content, filename, file.content_type
    )

    ocr_used = bool(extracted_metadata.get("ocr_used"))
    use_mock = settings.AI_PARSE_MOCK
    fields = _mock_parse_fields(text, filename)
    fields["mock"] = use_mock

    if not use_mock and text.strip():
        llm_fields = await extract_fields_with_llm(text, filename)
        if llm_fields:
            fields = _merge_llm_fields(fields, llm_fields)

    if db is not None:
        from sqlalchemy import select
        from app.models.counterparty import Counterparty

        party_a, party_b, corrections = await fuzzy_match_counterparty_names(
            db,
            fields.get("party_a"),
            fields.get("party_b"),
        )
        if party_a is not None:
            fields["party_a"] = party_a
        if party_b is not None:
            fields["party_b"] = party_b
        if corrections:
            fields["counterparty_corrections"] = corrections
            fields["party_parse_warning"] = detect_party_parse_warning(
                fields.get("party_a"),
                fields.get("party_b"),
            )

        cp_result = await db.execute(
            select(Counterparty.name).where(Counterparty.status == 1)
        )
        cp_names = [row[0] for row in cp_result.all() if row[0]]
        fields = enrich_fields_with_dictionary(fields, cp_names)

    fields = _ensure_valid_title(fields, text, filename)

    fields["text_preview"] = text[:500]
    fields["full_text"] = text
    raw_from_meta = extracted_metadata.get("full_text_raw")
    if raw_from_meta:
        fields["full_text_raw"] = raw_from_meta
    fields["file_type"] = file_type
    fields["char_count"] = len(text)
    fields["ocr_used"] = ocr_used
    fields["needs_ocr"] = (
        not text.strip() and file_type == "pdf" and not settings.AI_OCR_ENABLED
    )
    fields["confidence"] = _compute_parse_confidence(
        fields,
        text=text,
        ocr_used=ocr_used,
        extracted_metadata=extracted_metadata,
    )

    return {
        "filename": filename,
        "fields": fields,
        "extracted_metadata": extracted_metadata,
        "ocr_used": ocr_used,
        "char_count": len(text),
        "layout_version": extracted_metadata.get("layout_version"),
        "ocr_engine": extracted_metadata.get("ocr_engine"),
        "document_json": extracted_metadata.get("document_json"),
    }
