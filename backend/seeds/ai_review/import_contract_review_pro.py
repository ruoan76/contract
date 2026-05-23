#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 contract-review-pro 的 CSV 生成 JSON 种子（见 docs/reference/contract-review-pro-seeds.md）。

用法（项目根目录）：
  python3 backend/seeds/ai_review/import_contract_review_pro.py

依赖：仅标准库。输入默认 backend/seeds/ai_review/raw/*.csv
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
OUT = ROOT / "generated"

# 平台 contract_type → 默认 ai_profile_key（上游中文合同类型名）
CONTRACT_TYPE_MAP = [
    {
        "contract_type": "purchase",
        "ai_profile_key": "买卖合同",
        "aliases": ["商品房买卖合同", "仓储合同", "承揽合同"],
    },
    {
        "contract_type": "sales",
        "ai_profile_key": "买卖合同",
        "aliases": ["产品代理销售合同"],
        "notes": "销售方视角，侧重价款与交付",
    },
    {
        "contract_type": "labor",
        "ai_profile_key": "劳动合同",
        "aliases": ["劳务派遣合同", "竞业限制协议"],
    },
    {
        "contract_type": "nda",
        "ai_profile_key": "技术转让合同",
        "aliases": ["保密协议", "技术开发合同"],
    },
    {
        "contract_type": "cooperation",
        "ai_profile_key": "服务合同",
        "aliases": ["合伙合同", "特许经营合同", "中介合同"],
    },
    {
        "contract_type": "legal-standard",
        "ai_profile_key": "服务合同",
        "aliases": ["法务制式合同"],
    },
    {
        "contract_type": "other",
        "ai_profile_key": "服务合同",
        "aliases": [],
        "notes": "通用兜底，可人工覆盖 ai_profile_key",
    },
]

# 上游 risk_level 中文 → 平台 risk_level
RISK_LEVEL_MAP = {
    "致命风险": "high",
    "重要风险": "high",
    "一般风险": "medium",
    "轻微瑕疵": "low",
}


def read_csv(name: str) -> list[dict]:
    path = RAW / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"缺少 {path}，请先下载上游 data/{name}.csv")
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def normalize_risk_labels(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append(
            {
                "id": r.get("label_id", "").strip(),
                "name": r.get("label_name", "").strip(),
                "category": r.get("category", "").strip(),
                "gate_id": r.get("typical_gate", "").strip(),
                "color": r.get("color_code", "").strip(),
            }
        )
    return out


def normalize_revision_routing(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        auto = str(r.get("auto_applicable", "")).strip().lower() in ("true", "1", "yes")
        out.append(
            {
                "issue_type": r.get("issue_type", "").strip(),
                "default_method": r.get("default_method", "comment").strip(),
                "auto_applicable": auto,
                "self_check_questions": r.get("self_check_questions", "").strip(),
                "notes": r.get("notes", "").strip(),
            }
        )
    return out


def normalize_checklists(rows: list[dict]) -> list[dict]:
    out = []
    for i, r in enumerate(rows, start=1):
        auto = str(r.get("auto_detectable", "")).strip().lower() in ("true", "1", "yes")
        rl = RISK_LEVEL_MAP.get(r.get("risk_level", "").strip(), "medium")
        out.append(
            {
                "id": i,
                "category": r.get("checklist_category", "").strip(),
                "item": r.get("checklist_item", "").strip(),
                "description": r.get("description", "").strip(),
                "applicable_contracts": r.get("applicable_contracts", "").strip(),
                "risk_level": rl,
                "gate_id": r.get("gate_category", "").strip(),
                "gate_priority": int(r.get("gate_priority") or 0),
                "auto_detectable": auto,
            }
        )
    return out


def label_name_to_id(labels: list[dict]) -> dict[str, str]:
    m = {}
    for lb in labels:
        m[lb["name"]] = lb["id"]
    return m


def normalize_risk_templates(rows: list[dict], label_map: dict[str, str]) -> list[dict]:
    out = []
    for r in rows:
        label_name = r.get("risk_label", "").strip()
        label_id = label_map.get(label_name, "")
        out.append(
            {
                "risk_id": r.get("risk_id", "").strip(),
                "profile_key": r.get("contract_type", "").strip(),
                "risk_type": r.get("risk_type", "").strip(),
                "clause_name": r.get("clause_name", "").strip(),
                "description": r.get("risk_description", "").strip(),
                "legal_basis": r.get("legal_basis", "").strip(),
                "suggestion": r.get("modification_suggestion", "").strip(),
                "impact": r.get("impact_analysis", "").strip(),
                "label_id": label_id,
                "label_name": label_name,
                "gate_id": r.get("gate_id", "").strip(),
                "revision_method": r.get("default_revision_method", "comment").strip(),
                "risk_level": RISK_LEVEL_MAP.get(r.get("risk_type", "").strip(), "medium"),
            }
        )
    return out


def normalize_contract_profiles(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        review_points = r.get("review_points", "")
        points = [p.strip() for p in re.split(r"[\n\\n]+", review_points) if p.strip()]
        out.append(
            {
                "profile_key": r.get("contract_type", "").strip(),
                "category": r.get("category", "").strip(),
                "core_risks": r.get("core_risks", "").strip(),
                "key_clauses": r.get("key_clauses", "").strip(),
                "legal_basis": r.get("legal_basis", "").strip(),
                "review_points": points,
                "gate_category": r.get("gate_category", "").strip(),
            }
        )
    return out


def filter_templates(templates: list[dict], profile_keys: set[str]) -> list[dict]:
    return [t for t in templates if t["profile_key"] in profile_keys or t["profile_key"] == "通用"]


def write_json(name: str, data: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote {path}")


def main() -> None:
    print("contract-review-pro → generated JSON")
    labels = normalize_risk_labels(read_csv("risk_labels"))
    write_json("risk_labels.json", {"version": "crp-v3.0", "count": len(labels), "items": labels})

    routing = normalize_revision_routing(read_csv("revision_routing"))
    write_json(
        "revision_routing.json",
        {"version": "crp-v3.0", "count": len(routing), "items": routing},
    )

    checklists = normalize_checklists(read_csv("review_checklists"))
    auto_only = [c for c in checklists if c["auto_detectable"]]
    write_json(
        "review_checklists.json",
        {
            "version": "crp-v3.0",
            "count": len(checklists),
            "auto_detectable_count": len(auto_only),
            "items": checklists,
        },
    )

    write_json(
        "contract_type_map.json",
        {"version": "crp-v3.0", "platform_mapping": CONTRACT_TYPE_MAP},
    )

    label_map = label_name_to_id(labels)
    all_templates = normalize_risk_templates(read_csv("risk_templates"), label_map)
    purchase_keys = {"买卖合同", "通用"}
    purchase_subset = filter_templates(all_templates, purchase_keys)
    write_json(
        "risk_templates.purchase.json",
        {
            "version": "crp-v3.0",
            "profile_keys": sorted(purchase_keys),
            "count": len(purchase_subset),
            "items": purchase_subset,
        },
    )

    ct_path = RAW / "contract_types.csv"
    if ct_path.exists():
        profiles = normalize_contract_profiles(read_csv("contract_types"))
        write_json(
            "contract_type_profiles.json",
            {"version": "crp-v3.0", "count": len(profiles), "items": profiles},
        )
    else:
        print("  skip contract_type_profiles.json (raw/contract_types.csv 缺失)")

    meta = {
        "source": "https://github.com/CSlawyer1985/contract-review-pro",
        "license": "MIT",
        "upstream_tag": "crp-v3.0",
        "generated_by": "import_contract_review_pro.py",
        "counts": {
            "risk_labels": len(labels),
            "revision_routing": len(routing),
            "review_checklists": len(checklists),
            "risk_templates_purchase": len(purchase_subset),
        },
    }
    write_json("manifest.json", meta)
    print("done.")


if __name__ == "__main__":
    main()
