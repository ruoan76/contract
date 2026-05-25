"""
相对方 CSV 导入 API 测试
"""
import io

import pytest


@pytest.mark.unit
class TestCounterpartiesImportAPI:
    """POST /api/v1/counterparties/import"""

    async def test_import_csv_creates_records(self, client_for_user):
        csv_content = (
            "name,credit_code,contact_name,contact_phone\n"
            "导入测试公司A,91110000IMPORT001,张三,13800000001\n"
            "导入测试公司B,91110000IMPORT002,李四,13800000002\n"
        )
        files = {"file": ("counterparties.csv", io.BytesIO(csv_content.encode("utf-8-sig")), "text/csv")}

        async with await client_for_user("admin") as admin:
            resp = await admin.post("/api/v1/counterparties/import", files=files)

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["created"] == 2
        assert data["skipped"] == 0
        assert data["errors"] == []

    async def test_import_skips_duplicate_credit_code(self, client_for_user):
        async with await client_for_user("admin") as admin:
            await admin.post(
                "/api/v1/counterparties/",
                json={"name": "已有公司", "credit_code": "91110000DUP0001"},
            )
            csv_content = "name,credit_code\n重复公司,91110000DUP0001\n新公司,91110000DUP0002\n"
            files = {"file": ("dup.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
            resp = await admin.post("/api/v1/counterparties/import", files=files)

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["created"] == 1
        assert data["skipped"] == 1
        assert len(data["errors"]) == 1

    async def test_drafter_cannot_import(self, client_for_user):
        csv_content = "name,credit_code\n测试,91110000NOAUTH01\n"
        files = {"file": ("x.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}

        async with await client_for_user("drafter") as drafter:
            resp = await drafter.post("/api/v1/counterparties/import", files=files)

        assert resp.status_code == 403
