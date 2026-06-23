# -*- coding: utf-8 -*-
"""OCR 指标与后处理单测。"""
from __future__ import annotations

import json
from pathlib import Path

from app.services.ai_review.ocr_metrics import character_error_rate, field_f1, text_similarity
from app.services.ai_review.ocr_postprocess import (
    apply_ocr_replacements,
    correct_party_name,
    enrich_fields_with_dictionary,
)
from app.services.contract_parse_service import _mock_parse_fields

MANIFEST = Path(__file__).resolve().parent / "fixtures" / "ocr" / "benchmark_manifest.json"


def test_character_error_rate_identical() -> None:
    assert character_error_rate("甲方：测试", "甲方：测试") == 0.0


def test_character_error_rate_completely_wrong() -> None:
    assert character_error_rate("abc", "") == 1.0


def test_field_f1_exact_match() -> None:
    ref = {"party_a": "甲公司", "party_b": "乙公司", "amount": 1000}
    pred = {"party_a": "甲公司", "party_b": "乙公司", "amount": 1000}
    scores = field_f1(ref, pred)
    assert scores["f1"] == 1.0


def test_apply_ocr_replacements() -> None:
    out = apply_ocr_replacements("浪潮软住股俭直限公司")
    assert "软件" in out
    assert "股份" in out


def test_correct_party_name_with_candidates() -> None:
    fixed, changed = correct_party_name(
        "浪潮软住股俭直限公司",
        ["浪潮软件股份有限公司"],
        threshold=0.6,
    )
    assert changed is True
    assert fixed == "浪潮软件股份有限公司"


def test_enrich_fields_with_dictionary() -> None:
    fields = _mock_parse_fields(
        "甲方：甘-省烟堂公司\n乙方：浪潮软住股俭直限公司\n",
        "test.pdf",
    )
    enriched = enrich_fields_with_dictionary(
        fields,
        ["甘肃省烟草公司兰州市公司", "浪潮软件股份有限公司"],
    )
    assert enriched.get("party_b") == "浪潮软件股份有限公司"


def test_benchmark_manifest_postprocess_case() -> None:
    cases = json.loads(MANIFEST.read_text(encoding="utf-8"))
    noise = next(c for c in cases if c["id"] == "ocr_noise_reference")
    hypothesis = apply_ocr_replacements(noise["hypothesis_for_postprocess"])
    cer = character_error_rate(noise["reference"], hypothesis)
    assert cer <= noise["max_cer"]


def test_text_similarity() -> None:
    assert text_similarity("abc", "abc") == 1.0
