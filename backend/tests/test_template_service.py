"""模板发布状态机测试"""
import pytest
from fastapi import HTTPException

from app.models.template import ContractTemplate
from app.services.template_service import (
    approve_publish,
    create_template,
    deprecate_template,
    reject_publish,
    submit_for_publish,
)


@pytest.mark.unit
class TestTemplateStateMachine:
    async def test_draft_to_pending_to_published(self, db_session):
        t = await create_template(
            db_session, "采购模板", "purchase", "正文", creator_id=1
        )
        assert t["status"] == "draft"

        pending = await submit_for_publish(db_session, t["id"])
        assert pending["status"] == "pending_publish"

        published = await approve_publish(db_session, t["id"])
        assert published["status"] == "published"
        assert published["version"] == 2

    async def test_reject_publish_returns_draft(self, db_session):
        t = await create_template(
            db_session, "服务模板", "service", "内容", creator_id=1
        )
        await submit_for_publish(db_session, t["id"])
        rejected = await reject_publish(db_session, t["id"])
        assert rejected["status"] == "draft"

    async def test_deprecate_only_from_published(self, db_session):
        t = await create_template(
            db_session, "废止测试", "purchase", "内容", creator_id=1
        )
        with pytest.raises(HTTPException, match="仅已发布模板可废止"):
            await deprecate_template(db_session, t["id"])

        await submit_for_publish(db_session, t["id"])
        await approve_publish(db_session, t["id"])
        deprecated = await deprecate_template(db_session, t["id"])
        assert deprecated["status"] == "deprecated"

    async def test_submit_publish_invalid_state(self, db_session):
        t = await create_template(
            db_session, "状态校验", "purchase", "内容", creator_id=1
        )
        await submit_for_publish(db_session, t["id"])
        with pytest.raises(HTTPException, match="仅草稿状态可提交发布"):
            await submit_for_publish(db_session, t["id"])

    async def test_approve_publish_rejects_draft(self, db_session):
        """approve-publish 不可从 draft 跳过审批"""
        t = await create_template(
            db_session, "跳过审批", "purchase", "内容", creator_id=1
        )
        with pytest.raises(HTTPException, match="仅待发布状态可批准"):
            await approve_publish(db_session, t["id"])

    async def test_publish_template_backward_compat(self, db_session):
        """publish_template 兼容从 draft 直接发布"""
        from app.services.template_service import publish_template

        t = await create_template(
            db_session, "兼容发布", "purchase", "内容", creator_id=1
        )
        published = await publish_template(db_session, t["id"])
        assert published["status"] == "published"
        assert published["version"] == 2
