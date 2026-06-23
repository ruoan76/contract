# -*- coding: utf-8 -*-
"""ConfigStore 与 JSON fallback 一致性。"""
import json
from pathlib import Path

import pytest

from app.services.ai_review import config_store
from app.services.ai_review.config_seed import import_from_json_seeds


GENERATED = Path(__file__).resolve().parents[1] / "seeds" / "ai_review" / "generated"


@pytest.fixture(autouse=True)
def _clear_caches():
    config_store.clear_config_cache()
    yield
    config_store.clear_config_cache()


def test_json_fallback_checklist_count():
    raw = json.loads((GENERATED / "review_checklists.json").read_text(encoding="utf-8"))
    data = config_store.get_review_checklists()
    assert data.get("count") == raw.get("count")
    assert len(data.get("items", [])) == len(raw.get("items", []))


def test_json_fallback_labels_count():
    raw = json.loads((GENERATED / "risk_labels.json").read_text(encoding="utf-8"))
    data = config_store.get_risk_labels()
    assert len(data.get("items", [])) == len(raw.get("items", []))


@pytest.mark.asyncio
async def test_db_cache_after_seed(db_session):
    version = "test-seed-version"
    await import_from_json_seeds(version)
    ver = await config_store.refresh_config_cache(db_session)
    assert ver == version
    cl = config_store.get_review_checklists()
    assert cl.get("count", 0) >= 50
    rules = config_store.get_hard_rules()
    assert any(r.get("rule_id") == "PR-001" for r in rules)
