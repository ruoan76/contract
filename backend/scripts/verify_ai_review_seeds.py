#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验 AI 审查种子 JSON 与 manifest 计数一致。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
GENERATED = BACKEND / "seeds" / "ai_review" / "generated"
LEGAL = BACKEND / "seeds" / "ai_review" / "legal_snippets.json"

EXPECTED_HARD_RULE_IDS = {
    "PR-001",
    "CK-46",
    "CK-47",
    "CK-48",
    "CK-49",
    "CK-50",
    "CK-52",
    "CK-53",
    "TH-BOARD",
    "TH-BLACKLIST",
    "RL-L01",
    "RL-L08-1",
    "RL-L01-2",
}


def main() -> int:
    errors: list[str] = []
    manifest = json.loads((GENERATED / "manifest.json").read_text(encoding="utf-8"))
    counts = manifest.get("counts", {})

    for key, fname in (
        ("risk_labels", "risk_labels.json"),
        ("revision_routing", "revision_routing.json"),
        ("review_checklists", "review_checklists.json"),
    ):
        data = json.loads((GENERATED / fname).read_text(encoding="utf-8"))
        n = len(data.get("items", []))
        exp = counts.get(key)
        if n != exp:
            errors.append(f"{fname}: items={n} manifest={exp}")

    cl = json.loads((GENERATED / "review_checklists.json").read_text(encoding="utf-8"))
    auto_ids = [i["id"] for i in cl.get("items", []) if i.get("auto_detectable")]
    if sorted(auto_ids) != [44, 45, 51]:
        errors.append(f"auto_detectable ids expected [44,45,51], got {auto_ids}")

    if LEGAL.is_file():
        legal = json.loads(LEGAL.read_text(encoding="utf-8"))
        legal_n = len(legal) if isinstance(legal, list) else len(legal.get("items", []))
        if legal_n < 1:
            errors.append("legal_snippets.json empty")
    else:
        errors.append("legal_snippets.json missing")

    sys.path.insert(0, str(BACKEND))
    from app.services.ai_review.config_seed import DEFAULT_HARD_RULES, DETECT_PRESETS

    rule_ids = {r["rule_id"] for r in DEFAULT_HARD_RULES}
    if rule_ids != EXPECTED_HARD_RULE_IDS:
        missing = EXPECTED_HARD_RULE_IDS - rule_ids
        extra = rule_ids - EXPECTED_HARD_RULE_IDS
        if missing:
            errors.append(f"DEFAULT_HARD_RULES missing: {sorted(missing)}")
        if extra:
            errors.append(f"DEFAULT_HARD_RULES extra: {sorted(extra)}")

    for lid in auto_ids:
        if lid not in DETECT_PRESETS:
            errors.append(f"legacy_id {lid} auto_detectable but no DETECT_PRESETS")

    if errors:
        print("AI review seed verification FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(
        "AI review seed verification OK:",
        f"labels={counts['risk_labels']}",
        f"routing={counts['revision_routing']}",
        f"checklists={counts['review_checklists']}",
        f"hard_rules={len(DEFAULT_HARD_RULES)}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
