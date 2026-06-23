#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR 基准评测 — CER 与字段 F1。

用法:
  python scripts/benchmark_ocr.py
  python scripts/benchmark_ocr.py --engine easyocr
  python scripts/benchmark_ocr.py --engine rapidocr --json-out /tmp/ocr_bench.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import fitz
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.services.ai_review.ocr import ocr_image_array
from app.services.ai_review.ocr_engine import clear_engine_cache
from app.services.ai_review.ocr_layout import layout_ocr_blocks
from app.services.ai_review.ocr_metrics import character_error_rate, field_f1
from app.services.ai_review.ocr_postprocess import apply_ocr_replacements
from app.services.contract_parse_service import _mock_parse_fields

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "ocr"
MANIFEST = FIXTURES / "benchmark_manifest.json"
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _render_text_page(text: str, *, width: int = 595, height: int = 842) -> np.ndarray:
    """将纯文本渲染为图像供 OCR 评测。"""
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)
    rect = fitz.Rect(50, 50, width - 50, height - 50)
    page.insert_textbox(
        rect,
        text,
        fontsize=11,
        fontname="china-s",
    )
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    channels = pix.n
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, channels)
    if channels == 4:
        arr = arr[:, :, :3]
    doc.close()
    return arr


def _run_case(case: dict, engine: str) -> dict:
    case_id = case["id"]
    reference = case.get("reference", "")
    max_cer = float(case.get("max_cer", 0.25))

    if case.get("skip_ocr"):
        hypothesis = apply_ocr_replacements(case.get("hypothesis_for_postprocess", reference))
        cer = character_error_rate(reference, hypothesis)
        fields = _mock_parse_fields(hypothesis, f"{case_id}.pdf")
        ref_fields = case.get("fields") or {}
        f1 = field_f1(ref_fields, fields) if ref_fields else {"f1": 1.0}
        return {
            "id": case_id,
            "engine": "postprocess",
            "cer": cer,
            "max_cer": max_cer,
            "cer_pass": cer <= max_cer,
            "field_f1": f1,
            "elapsed_ms": 0,
        }

    if case.get("type") == "pdf_page":
        pdf_path = BACKEND_ROOT / case["pdf"]
        if not pdf_path.is_file():
            return {
                "id": case_id,
                "skipped": True,
                "reason": f"PDF 不存在: {pdf_path}",
            }
        page_index = int(case.get("page", 0))
        doc = fitz.open(str(pdf_path))
        try:
            page = doc[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            channels = pix.n
            arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, channels
            )
            if channels == 4:
                arr = arr[:, :, :3]
        finally:
            doc.close()
        t0 = time.perf_counter()
        page_result = ocr_image_array(arr, engine_name=engine)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        easy_format = page_result.to_easyocr_format()
        hypothesis = layout_ocr_blocks(easy_format, min_conf=float(settings.AI_OCR_MIN_CONFIDENCE))
        hypothesis = apply_ocr_replacements(hypothesis)
        cer = character_error_rate(reference, hypothesis)
        return {
            "id": case_id,
            "engine": engine,
            "cer": round(cer, 4),
            "max_cer": max_cer,
            "cer_pass": cer <= max_cer,
            "avg_confidence": round(page_result.avg_confidence, 4),
            "elapsed_ms": elapsed_ms,
            "pdf": str(pdf_path.name),
        }

    image = _render_text_page(reference)
    t0 = time.perf_counter()
    page_result = ocr_image_array(image, engine_name=engine)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    easy_format = page_result.to_easyocr_format()
    hypothesis = layout_ocr_blocks(easy_format, min_conf=float(settings.AI_OCR_MIN_CONFIDENCE))
    hypothesis = apply_ocr_replacements(hypothesis)
    cer = character_error_rate(reference, hypothesis)
    fields = _mock_parse_fields(hypothesis, f"{case_id}.pdf")
    ref_fields = case.get("fields") or {}
    f1 = field_f1(ref_fields, fields) if ref_fields else {"f1": 1.0}

    return {
        "id": case_id,
        "engine": engine,
        "cer": round(cer, 4),
        "max_cer": max_cer,
        "cer_pass": cer <= max_cer,
        "avg_confidence": round(page_result.avg_confidence, 4),
        "needs_review": page_result.needs_review,
        "field_f1": {k: round(v, 4) if isinstance(v, float) else v for k, v in f1.items()},
        "elapsed_ms": elapsed_ms,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR 基准评测")
    parser.add_argument(
        "--engine",
        default=settings.AI_OCR_ENGINE,
        choices=["easyocr", "rapidocr"],
        help="OCR 引擎",
    )
    parser.add_argument("--json-out", type=Path, default=None, help="写入 JSON 报告")
    parser.add_argument("--skip-heavy", action="store_true", help="仅跑 skip_ocr / 轻量用例")
    parser.add_argument("--skip-ci", action="store_true", help="跳过 skip_ci 的真实 PDF 用例")
    args = parser.parse_args()

    if not MANIFEST.is_file():
        print(f"错误: 找不到基准清单 {MANIFEST}", file=sys.stderr)
        return 1

    cases = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if args.skip_heavy:
        cases = [c for c in cases if c.get("skip_ocr")]
    if args.skip_ci:
        cases = [c for c in cases if not c.get("skip_ci")]

    clear_engine_cache()
    results: list[dict] = []
    for case in cases:
        print(f"评测 {case['id']} …", flush=True)
        try:
            row = _run_case(case, args.engine)
            results.append(row)
            if row.get("skipped"):
                print(f"  跳过: {row.get('reason')}")
                continue
            status = "PASS" if row.get("cer_pass") else "FAIL"
            print(f"  CER={row.get('cer', 0):.3f} [{status}] conf={row.get('avg_confidence', '—')} {row.get('elapsed_ms', 0)}ms")
        except Exception as exc:
            print(f"  错误: {exc}", file=sys.stderr)
            results.append({"id": case["id"], "error": str(exc)})

    passed = sum(1 for r in results if r.get("cer_pass"))
    total = sum(1 for r in results if "cer_pass" in r)
    avg_cer = sum(r.get("cer", 0) for r in results if "cer" in r) / max(1, total)
    summary = {
        "engine": args.engine,
        "cases": len(results),
        "cer_pass": passed,
        "cer_total": total,
        "avg_cer": round(avg_cer, 4),
        "results": results,
    }
    print(f"\n汇总: {passed}/{total} 通过, avg_cer={avg_cer:.3f}")

    if args.json_out:
        args.json_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"报告已写入 {args.json_out}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
