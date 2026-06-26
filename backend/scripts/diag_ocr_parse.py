#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR/解析诊断 — 记录 ocr_used、字数、甲方乙方与 party_parse_warning。

用法:
  python scripts/diag_ocr_parse.py /path/to/contract.pdf
  python scripts/diag_ocr_parse.py --api http://127.0.0.1:8000 /path/to/contract.pdf
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _login(base_url: str, username: str, password: str) -> str:
    r = httpx.post(
        f"{base_url}/api/v1/system/login",
        params={"username": username, "password": password},
        timeout=30.0,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("code") != 200:
        raise RuntimeError(f"登录失败: {data}")
    return data["data"]["token"]


def diag_via_api(pdf_path: Path, base_url: str, username: str, password: str) -> dict:
    token = _login(base_url, username, password)
    with httpx.Client(timeout=900.0) as client:
        with pdf_path.open("rb") as fh:
            r = client.post(
                f"{base_url}/api/v1/contracts/parse",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": (pdf_path.name, fh, "application/pdf")},
            )
        r.raise_for_status()
        payload = r.json()
    return payload.get("data") or {}


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR 解析诊断")
    parser.add_argument("pdf", type=Path, help="PDF 路径")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="API 基址")
    parser.add_argument("--user", default="drafter1")
    parser.add_argument("--password", default="admin123")
    parser.add_argument("--json-out", type=Path, default=None, help="写入 JSON 报告")
    args = parser.parse_args()

    if not args.pdf.is_file():
        print(f"错误: 找不到文件 {args.pdf}", file=sys.stderr)
        return 1

    data = diag_via_api(args.pdf, args.api, args.user, args.password)
    fields = data.get("fields") or {}
    report = {
        "filename": data.get("filename"),
        "ocr_used": data.get("ocr_used"),
        "char_count": data.get("char_count"),
        "party_a": fields.get("party_a"),
        "party_b": fields.get("party_b"),
        "party_parse_warning": fields.get("party_parse_warning"),
        "confidence": fields.get("confidence"),
        "parse_source": fields.get("parse_source"),
        "counterparty_corrections": fields.get("counterparty_corrections"),
        "extracted_metadata": data.get("extracted_metadata"),
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.json_out:
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"已写入 {args.json_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
