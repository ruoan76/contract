# -*- coding: utf-8 -*-
"""法条 CSV 批量导入。"""
import pytest
from sqlalchemy import select

from app.models.ai_review_config import AILegalSnippet
from app.services.ai_review.config_admin_service import import_legal_snippets_csv


@pytest.mark.asyncio
async def test_import_legal_snippets_csv_upsert(db_session):
    csv_text = """snippet_id,keywords,text,enabled
LB-CSV-1,"违约,赔偿",条文一,true
LB-CSV-2,保密,条文二,false
"""
    r1 = await import_legal_snippets_csv(db_session, csv_text)
    assert r1["created"] == 2
    assert r1["updated"] == 0
    assert r1["skipped"] == 0
    await db_session.commit()

    row1 = await db_session.scalar(
        select(AILegalSnippet).where(AILegalSnippet.snippet_id == "LB-CSV-1")
    )
    assert row1 is not None
    assert "违约" in row1.keywords
    assert row1.text == "条文一"
    assert row1.enabled is True

    csv_update = """snippet_id,keywords,text,enabled
LB-CSV-1,更新关键词,更新后的条文,false
"""
    r2 = await import_legal_snippets_csv(db_session, csv_update)
    assert r2["created"] == 0
    assert r2["updated"] == 1
    await db_session.commit()

    row1b = await db_session.scalar(
        select(AILegalSnippet).where(AILegalSnippet.snippet_id == "LB-CSV-1")
    )
    assert row1b.text == "更新后的条文"
    assert row1b.enabled is False
    assert "更新关键词" in row1b.keywords


@pytest.mark.asyncio
async def test_import_legal_snippets_csv_skips_missing_fields(db_session):
    csv_text = """snippet_id,keywords,text,enabled
,关键词,缺 ID 的行,true
LB-SKIP-NO-TEXT,关键词,,true
LB-OK,关键词,正常条文,true
"""
    r = await import_legal_snippets_csv(db_session, csv_text)
    assert r["created"] == 1
    assert r["skipped"] >= 2
    assert len(r["errors"]) >= 2
