import pytest
from httpx import AsyncClient
from kosatka_master.models.client import Client
from kosatka_master.models.node import Node
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_subscription_success(client: AsyncClient, db_session: AsyncSession):
    # 1. Setup: Create a client and some nodes
    sub_token = "test-token-123"
    test_client = Client(
        external_id="ext-1",
        email="test@example.com",
        sub_token=sub_token,
        sub_enabled=True,
    )
    db_session.add(test_client)

    node = Node(
        name="test-node",
        address="1.2.3.4:443",
        provider_type="vless",
        is_active=True,
        role="standalone",
        metadata_json={
            "port": 443,
            "tls": True,
            "country_code": "US",
            "country_name": "United States",
        },
    )
    db_session.add(node)
    await db_session.commit()

    # 2. Action: Request the subscription
    response = await client.get(f"/sub/{sub_token}")

    # 3. Assert: Verify response
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/x-yaml; charset=utf-8"
    assert "subscription-userinfo" in response.headers
    assert "profile-update-interval" in response.headers
    assert "proxies" in response.text
    assert "test-node" in response.text


@pytest.mark.asyncio
async def test_get_subscription_not_found(client: AsyncClient):
    response = await client.get("/sub/non-existent-token")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_subscription_disabled(client: AsyncClient, db_session: AsyncSession):
    # Setup: Create a disabled client
    sub_token = "disabled-token"
    test_client = Client(
        external_id="ext-2",
        sub_token=sub_token,
        sub_enabled=False,
    )
    db_session.add(test_client)
    await db_session.commit()

    response = await client.get(f"/sub/{sub_token}")
    assert response.status_code == 404
