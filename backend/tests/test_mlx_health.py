# -*- coding: utf-8 -*-
"""MLX 可达性探测测试。"""
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings


@pytest.mark.asyncio
async def test_check_mlx_reachable_mock_mode():
    from app.services.ai_review.mlx_health import check_mlx_reachable

    with patch.object(settings, "AI_REVIEW_MOCK", True):
        ok, msg = await check_mlx_reachable()
    assert ok is True
    assert msg == "mock mode"


@pytest.mark.asyncio
async def test_check_mlx_reachable_ok():
    from app.services.ai_review.mlx_health import check_mlx_reachable

    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(settings, "AI_REVIEW_MOCK", False), patch(
        "app.services.ai_review.mlx_health.httpx.AsyncClient",
        return_value=mock_client,
    ):
        ok, msg = await check_mlx_reachable()
    assert ok is True
    assert msg == "ok"


@pytest.mark.asyncio
async def test_check_mlx_reachable_connect_error():
    import httpx
    from app.services.ai_review.mlx_health import check_mlx_reachable, mlx_unavailable_detail

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(settings, "AI_REVIEW_MOCK", False), patch(
        "app.services.ai_review.mlx_health.httpx.AsyncClient",
        return_value=mock_client,
    ):
        ok, msg = await check_mlx_reachable()
    assert ok is False
    assert "无法连接" in msg
    detail = mlx_unavailable_detail(msg)
    assert "mlx_lm.server" in detail
