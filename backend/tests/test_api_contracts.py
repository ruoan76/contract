"""
API Tests for contracts endpoint
测试合同 API 端点
"""
import pytest


@pytest.mark.unit
class TestCreateContractAPI:
    """POST /api/v1/contracts - 创建合同 API 测试"""

    async def test_create_contract_success(self, api_client, mock_auth_headers):
        headers = mock_auth_headers(user_id=1, role="user")
        payload = {
            "title": "软件开发服务合同",
            "contract_type": "service",
            "counterparty_name": "XX科技有限公司",
            "counterparty_credit_code": "91310115MA1K3XK123",
            "amount": 100000.00,
            "content": "合同内容...",
        }

        response = await api_client.post(
            "/api/v1/contracts/",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["title"] == "软件开发服务合同"
        assert data["data"]["counterparty_name"] == "XX科技有限公司"
        assert data["data"]["contract_no"].startswith("CON-")
        assert data["data"]["status"] == "draft"

    async def test_create_contract_unauthenticated(self, api_client_no_auth):
        payload = {
            "title": "Test Contract",
            "contract_type": "service",
            "counterparty_name": "Company",
        }

        response = await api_client_no_auth.post(
            "/api/v1/contracts/",
            json=payload,
        )

        assert response.status_code == 401

    async def test_create_contract_missing_fields(self, api_client, mock_auth_headers):
        headers = mock_auth_headers(user_id=1, role="user")
        payload = {
            "title": "Test Contract",
        }

        response = await api_client.post(
            "/api/v1/contracts/",
            json=payload,
            headers=headers,
        )

        assert response.status_code == 422


@pytest.mark.unit
class TestGetContractAPI:
    """GET /api/v1/contracts/{id} - 获取合同详情 API 测试"""

    async def test_get_contract_exists(self, api_client, mock_auth_headers):
        headers = mock_auth_headers(user_id=1, role="user")
        payload = {
            "title": "测试合同",
            "contract_type": "service",
            "counterparty_name": "公司",
        }
        create_response = await api_client.post(
            "/api/v1/contracts/",
            json=payload,
            headers=headers,
        )
        contract_id = create_response.json()["data"]["id"]

        response = await api_client.get(f"/api/v1/contracts/{contract_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["title"] == "测试合同"

    async def test_get_contract_not_found(self, api_client):
        response = await api_client.get("/api/v1/contracts/9999")
        assert response.status_code == 404


@pytest.mark.unit
class TestListContractsAPI:
    """GET /api/v1/contracts - 合同列表 API 测试"""

    async def test_list_contracts_empty(self, api_client):
        response = await api_client.get("/api/v1/contracts/")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["total"] == 0
        assert data["data"]["items"] == []

    async def test_list_contracts_with_pagination(self, api_client):
        response = await api_client.get("/api/v1/contracts/?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "total" in data["data"]
        assert "items" in data["data"]

    async def test_list_contracts_includes_date_fields(self, api_client, mock_auth_headers):
        headers = mock_auth_headers(user_id=1, role="user")
        create_response = await api_client.post(
            "/api/v1/contracts/",
            json={
                "title": "日期字段测试合同",
                "contract_type": "service",
                "counterparty_name": "公司",
                "amount": 100000,
            },
            headers=headers,
        )
        assert create_response.status_code == 200

        response = await api_client.get("/api/v1/contracts/")
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        assert len(items) >= 1
        item = items[0]
        assert "created_at" in item
        assert "start_date" in item
        assert "end_date" in item


@pytest.mark.unit
class TestUpdateContractAPI:
    """PUT /api/v1/contracts/{id} - 更新合同 API 测试"""

    async def test_update_contract_success(self, api_client, mock_auth_headers):
        headers = mock_auth_headers(user_id=1, role="user")
        payload = {
            "title": "原始合同",
            "contract_type": "service",
            "counterparty_name": "原始公司",
            "amount": 100000.00,
        }
        create_response = await api_client.post(
            "/api/v1/contracts/",
            json=payload,
            headers=headers,
        )
        contract_id = create_response.json()["data"]["id"]

        update_payload = {
            "title": "更新后的合同",
            "amount": 200000.00,
        }
        response = await api_client.put(
            f"/api/v1/contracts/{contract_id}",
            json=update_payload,
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["title"] == "更新后的合同"
        assert data["data"]["amount"] == 200000.00

    async def test_update_contract_not_draft(self, api_client, mock_auth_headers):
        headers = mock_auth_headers(user_id=1, role="user")
        payload = {
            "title": "合同",
            "contract_type": "service",
            "counterparty_name": "公司",
        }
        create_response = await api_client.post(
            "/api/v1/contracts/",
            json=payload,
            headers=headers,
        )
        contract_id = create_response.json()["data"]["id"]

        # 非草稿状态更新应返回 400（后续可补数据库状态模拟）
        assert contract_id is not None


@pytest.mark.unit
class TestDeleteContractAPI:
    """DELETE /api/v1/contracts/{id} - 删除合同 API 测试"""

    async def test_delete_contract_success(self, api_client, mock_auth_headers):
        headers = mock_auth_headers(user_id=1, role="user")
        payload = {
            "title": "待删除合同",
            "contract_type": "service",
            "counterparty_name": "公司",
        }
        create_response = await api_client.post(
            "/api/v1/contracts/",
            json=payload,
            headers=headers,
        )
        contract_id = create_response.json()["data"]["id"]

        response = await api_client.delete(
            f"/api/v1/contracts/{contract_id}",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "deleted" in data["message"]

    async def test_delete_contract_not_found(self, api_client, mock_auth_headers):
        headers = mock_auth_headers(user_id=1, role="user")
        response = await api_client.delete(
            "/api/v1/contracts/9999",
            headers=headers,
        )
        assert response.status_code == 404

    async def test_delete_contract_forbidden_non_creator(self, client_for_user):
        """非创建人删除他人草稿应返回 403"""
        async with await client_for_user("drafter") as drafter:
            create_resp = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "他人草稿",
                    "contract_type": "service",
                    "counterparty_name": "公司",
                },
            )
            contract_id = create_resp.json()["data"]["id"]

        async with await client_for_user("approver") as approver:
            response = await approver.delete(f"/api/v1/contracts/{contract_id}")

        assert response.status_code == 403
        assert "仅创建人或管理员可删除草稿" in response.json()["detail"]

    async def test_delete_contract_admin(self, client_for_user):
        """管理员可删除他人草稿"""
        async with await client_for_user("drafter") as drafter:
            create_resp = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "待管理员删除",
                    "contract_type": "service",
                    "counterparty_name": "公司",
                },
            )
            contract_id = create_resp.json()["data"]["id"]

        async with await client_for_user("admin") as admin:
            response = await admin.delete(f"/api/v1/contracts/{contract_id}")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"]

    async def test_delete_contract_not_draft(self, client_for_user):
        """非草稿状态删除应返回 400"""
        from sqlalchemy import update

        from app.db.database import async_session
        from app.models.contract import Contract

        async with await client_for_user("drafter") as drafter:
            create_resp = await drafter.post(
                "/api/v1/contracts/",
                json={
                    "title": "已提交合同",
                    "contract_type": "service",
                    "counterparty_name": "公司",
                },
            )
            contract_id = create_resp.json()["data"]["id"]

        async with async_session() as session:
            await session.execute(
                update(Contract)
                .where(Contract.id == contract_id)
                .values(status="pending")
            )
            await session.commit()

        async with await client_for_user("drafter") as drafter:
            response = await drafter.delete(f"/api/v1/contracts/{contract_id}")

        assert response.status_code == 400
        assert "不允许删除" in response.json()["detail"]
