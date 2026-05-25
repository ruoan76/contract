"""合同文件解析 — 文本提取 + 字段识别（支持 mock）"""
from __future__ import annotations

import os
import re
import tempfile
from typing import Any, Optional

from fastapi import UploadFile

from app.core.config import settings
from app.services.ai_review.text_extractor import extract_text


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

    title = None
    for line in text.splitlines()[:5]:
        line = line.strip()
        if line and len(line) >= 4:
            title = line[:120]
            break
    if not title:
        title = os.path.splitext(filename)[0] or "未命名合同"

    return {
        "title": title,
        "party_a": party_a,
        "party_b": party_b,
        "amount": amount,
        "currency": "CNY",
        "contract_type": "service" if "服务" in text else "purchase",
        "start_date": None,
        "end_date": None,
        "confidence": 0.75 if text.strip() else 0.3,
        "mock": True,
    }


async def parse_contract_file(file: UploadFile) -> dict[str, Any]:
    """
    上传合同文件，提取文本并返回解析字段。

    AI_PARSE_MOCK=1（默认）时使用启发式 mock；否则同样返回启发式结果并标记 mock=False。
    """
    filename = file.filename or "upload.txt"
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise ValueError(f"文件超过大小限制 {settings.MAX_FILE_SIZE} 字节")

    file_type = _guess_file_type(filename, file.content_type)
    suffix = f".{file_type}" if file_type else ""

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    extracted_metadata: dict[str, Any] = {}
    try:
        if file_type == "pdf":
            extracted = await extract_text(tmp_path, "pdf")
        elif file_type == "docx":
            extracted = await extract_text(tmp_path, "docx")
        else:
            extracted = await extract_text(tmp_path, "txt")
        text = extracted.full_text or ""
        extracted_metadata = extracted.metadata or {}
    except Exception:
        # PDF/DOCX stub：无法解析时尝试按文本解码
        text = ""
        for enc in ("utf-8", "gbk", "latin-1"):
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if not text:
            text = content.decode("utf-8", errors="replace")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    use_mock = settings.AI_PARSE_MOCK
    fields = _mock_parse_fields(text, filename)
    fields["mock"] = use_mock
    fields["text_preview"] = text[:500]
    fields["file_type"] = file_type
    fields["char_count"] = len(text)

    return {
        "filename": filename,
        "fields": fields,
        "extracted_metadata": extracted_metadata,
    }
