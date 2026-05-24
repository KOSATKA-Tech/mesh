import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from kosatka_master.services.subscription_engine import SubscriptionEngine
from kosatka_master.models.subscription import Subscription
from kosatka_master.models.client import Client
from kosatka_master.models.node import Node
from sqlalchemy import select


@pytest.mark.asyncio
async def test_subscription_expiration_lifecycle(db_session):
    # 1. Setup: Create a node and a client
    node = Node(name="n1", address="http://agent:8010", provider_type="wireguard", is_active=True)
    db_session.add(node)
    await db_session.commit()
    
    client = Client(external_id="user1", node_id=node.id, is_active=True)
    db_session.add(client)
    await db_session.commit()
    
    # 2. Add an expired subscription
    engine = SubscriptionEngine(db_session)
    expired_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    await engine.create_subscription(client.id, "Pro Plan", expired_date)
    
    # 3. Run check_expirations
    with patch("kosatka_master.api.v1.clients._call_agent", AsyncMock()) as mock_call:
        await engine.check_expirations()
        
        # Verify client is deactivated
        await db_session.refresh(client)
        assert client.is_active is False
        
        # Verify agent was called to revoke access
        mock_call.assert_called_once()
        args, kwargs = mock_call.call_args
        assert args[1] == "DELETE"
        assert args[2] == "/clients/user1"


@pytest.mark.asyncio
async def test_subscription_active_prevents_deactivation(db_session):
    client = Client(external_id="user2", is_active=True)
    db_session.add(client)
    await db_session.commit()
    
    engine = SubscriptionEngine(db_session)
    # One expired, one active
    expired_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    active_date = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
    
    await engine.create_subscription(client.id, "Old Plan", expired_date)
    await engine.create_subscription(client.id, "New Plan", active_date)
    
    await engine.check_expirations()
    
    await db_session.refresh(client)
    # Client should still be active because of the "New Plan"
    assert client.is_active is True


@pytest.mark.asyncio
async def test_provision_requires_subscription(client, db_session):
    from kosatka_master.config import settings
    headers = {"X-Kosatka-Key": settings.api_key}
    
    # Create node
    await client.post("/api/v1/nodes/", json={"name": "n3", "address": "http://a3", "provider_type": "wireguard"}, headers=headers)
    
    # Try to provision without subscription
    response = await client.post("/api/v1/clients/provision/", json={"external_id": "c3", "protocol": "wireguard"}, headers=headers)
    assert response.status_code == 403
    assert "no active subscription" in response.json()["detail"]
    
    # Add subscription
    # First find client id
    res = await db_session.execute(select(Client).where(Client.external_id == "c3"))
    db_client = res.scalar_one()
    
    future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
    await client.post("/api/v1/subscriptions/", json={
        "client_id": db_client.id,
        "plan_name": "Monthly",
        "expires_at": future.isoformat()
    }, headers=headers)
    
    # Try again
    with patch("kosatka_master.api.v1.clients._call_agent") as mock_call:
        mock_call.return_value = {"id": "c3", "status": "added", "config_text": "ok"}
        response = await client.post("/api/v1/clients/provision/", json={"external_id": "c3", "protocol": "wireguard"}, headers=headers)
        assert response.status_code == 200
