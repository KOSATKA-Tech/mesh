from unittest.mock import patch

import pytest
from kosatka_master.config import settings


@pytest.mark.asyncio
async def test_nodes_list(client):
    headers = {"X-Kosatka-Key": settings.api_key}
    response = await client.get("/api/v1/nodes/", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_node_registration_and_health(client):
    headers = {"X-Kosatka-Key": settings.api_key}
    node_data = {"name": "test-node", "address": "http://1.2.3.4:8010", "provider_type": "agent"}

    # Registration
    response = await client.post("/api/v1/nodes/", json=node_data, headers=headers)
    assert response.status_code == 200
    node_id = response.json()["id"]

    # Health check success
    with patch(
        "kosatka_master.services.providers.agent_provider.AgentNodeProvider.sync_node"
    ) as mock_sync:
        mock_sync.return_value = {"status": "ok", "provider": "wireguard"}
        response = await client.get(f"/api/v1/nodes/{node_id}/health/", headers=headers)
        assert response.status_code == 200
        assert response.json()["provider_type"] == "wireguard"
        assert response.json()["status"] == "online"

    # Health check failure
    with patch(
        "kosatka_master.services.providers.agent_provider.AgentNodeProvider.sync_node"
    ) as mock_sync:
        mock_sync.return_value = None
        response = await client.get(f"/api/v1/nodes/{node_id}/health/", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "offline"


@pytest.mark.asyncio
async def test_node_get_detail(client):
    headers = {"X-Kosatka-Key": settings.api_key}
    resp = await client.post(
        "/api/v1/nodes/", json={"name": "detail-node", "address": "addr"}, headers=headers
    )
    node_id = resp.json()["id"]

    response = await client.get(f"/api/v1/nodes/{node_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "detail-node"

    response = await client.get("/api/v1/nodes/888", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_node_delete(client):
    headers = {"X-Kosatka-Key": settings.api_key}
    # Create first
    resp = await client.post(
        "/api/v1/nodes/", json={"name": "to-delete", "address": "addr"}, headers=headers
    )
    node_id = resp.json()["id"]

    # Delete
    response = await client.delete(f"/api/v1/nodes/{node_id}", headers=headers)
    assert response.status_code == 200

    # Verify 404
    response = await client.get(f"/api/v1/nodes/{node_id}/health/", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_node_registration_upsert(client):
    headers = {"X-Kosatka-Key": settings.api_key}
    # 1. First registration
    await client.post("/api/v1/nodes/", json={"name": "upsert", "address": "a1"}, headers=headers)

    # 2. Re-registration (upsert)
    response = await client.post(
        "/api/v1/nodes/",
        json={"name": "upsert", "address": "a2", "api_key": "newkey"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["address"] == "a2"


@pytest.mark.asyncio
async def test_node_errors(client):
    headers = {"X-Kosatka-Key": settings.api_key}

    # Not found
    response = await client.get("/api/v1/nodes/999/health/", headers=headers)
    assert response.status_code == 404

    # Duplicate name (should upsert)
    await client.post("/api/v1/nodes/", json={"name": "dup", "address": "a1"}, headers=headers)
    response = await client.post(
        "/api/v1/nodes/", json={"name": "dup", "address": "a2"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["address"] == "a2"
