from unittest.mock import patch

import pytest
from kosatka_master.config import settings


@pytest.mark.asyncio
async def test_provision_client(client, db_session):
    headers = {"X-Kosatka-Key": settings.api_key}

    # 1. Create a node first so we have somewhere to provision
    await client.post(
        "/api/v1/nodes/",
        json={"name": "n1", "address": "http://a1", "provider_type": "wireguard"},
        headers=headers,
    )

    # Create client and subscription
    resp = await client.post("/api/v1/clients/", json={"external_id": "c1"}, headers=headers)
    cid = resp.json()["id"]
    from datetime import datetime, timedelta, timezone

    future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
    await client.post(
        "/api/v1/subscriptions/",
        json={"client_id": cid, "plan_name": "Test", "expires_at": future.isoformat()},
        headers=headers,
    )

    # 2. Mock agent call
    with patch("kosatka_master.api.v1.clients.call_agent") as mock_call:
        mock_call.return_value = {
            "client_id": "c1",
            "config_text": "wg-config",
            "address": "10.8.0.2/32",
        }

        response = await client.post(
            "/api/v1/clients/provision/",
            json={"external_id": "c1", "protocol": "wireguard"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["config_text"] == "wg-config"


@pytest.mark.asyncio
async def test_get_clients_list(client):
    headers = {"X-Kosatka-Key": settings.api_key}
    await client.post("/api/v1/clients/", json={"external_id": "user-list"}, headers=headers)
    response = await client.get("/api/v1/clients/", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_client_lifecycle(client):
    headers = {"X-Kosatka-Key": settings.api_key}
    # Create
    resp = await client.post("/api/v1/clients/", json={"external_id": "lifecycle"}, headers=headers)
    cid = resp.json()["id"]

    # Get
    response = await client.get(f"/api/v1/clients/{cid}", headers=headers)
    assert response.status_code == 200

    # Delete
    response = await client.delete(f"/api/v1/clients/{cid}", headers=headers)
    assert response.status_code == 200

    # Verify gone
    response = await client.get(f"/api/v1/clients/{cid}", headers=headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_provision_with_pin(client):
    headers = {"X-Kosatka-Key": settings.api_key}

    resp = await client.post(
        "/api/v1/nodes/",
        json={"name": "pin-node", "address": "http://pin", "provider_type": "xray"},
        headers=headers,
    )
    node_id = resp.json()["id"]

    # Create client and subscription
    resp = await client.post("/api/v1/clients/", json={"external_id": "c1"}, headers=headers)
    cid = resp.json()["id"]
    from datetime import datetime, timedelta, timezone

    future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
    await client.post(
        "/api/v1/subscriptions/",
        json={"client_id": cid, "plan_name": "Test", "expires_at": future.isoformat()},
        headers=headers,
    )

    with patch("kosatka_master.api.v1.clients.call_agent") as mock_call:
        mock_call.return_value = {"id": "c1", "status": "added"}

        # Provision pinned to node_id
        response = await client.post(
            "/api/v1/clients/provision/",
            json={"external_id": "c1", "protocol": "xray", "node_id": node_id},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["node_id"] == node_id


@pytest.mark.asyncio
async def test_get_client_config_edge_cases(client):
    headers = {"X-Kosatka-Key": settings.api_key}

    # 1. Unknown external_id
    response = await client.get("/api/v1/clients/by-external/unknown/config", headers=headers)
    assert response.status_code == 404

    # 2. Node inactive
    await client.post(
        "/api/v1/nodes/", json={"name": "inactive", "address": "addr"}, headers=headers
    )
    # The client above created nodes, but they are 'offline' by default
    # but 'is_active' is True.

    # Actually _pick_node checks is_active.

    # Add subscription for c3 to reach 503
    resp = await client.post("/api/v1/clients/", json={"external_id": "c3"}, headers=headers)
    cid = resp.json()["id"]
    from datetime import datetime, timedelta, timezone

    future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
    await client.post(
        "/api/v1/subscriptions/",
        json={"client_id": cid, "plan_name": "T", "expires_at": future.isoformat()},
        headers=headers,
    )

    # 3. No node for protocol
    response = await client.post(
        "/api/v1/clients/provision/",
        json={"external_id": "c3", "protocol": "unknown-proto"},
        headers=headers,
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_get_client_config(client):
    headers = {"X-Kosatka-Key": settings.api_key}

    # Pre-populate node and client
    await client.post(
        "/api/v1/nodes/",
        json={"name": "n2", "address": "http://a2", "provider_type": "wireguard"},
        headers=headers,
    )

    with patch("kosatka_master.api.v1.clients.call_agent") as mock_call:
        mock_call.return_value = {"config": "stored-config"}

        response = await client.get("/api/v1/clients/by-external/c1/config", headers=headers)
        # Should search nodes and find config
        assert response.status_code == 200
        assert response.json()["config"] == "stored-config"


@pytest.mark.asyncio
async def test_provision_errors(client):
    headers = {"X-Kosatka-Key": settings.api_key}

    # Add subscription for c2 to reach 503
    resp = await client.post("/api/v1/clients/", json={"external_id": "c2"}, headers=headers)
    cid = resp.json()["id"]
    from datetime import datetime, timedelta, timezone

    future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30)
    await client.post(
        "/api/v1/subscriptions/",
        json={"client_id": cid, "plan_name": "T", "expires_at": future.isoformat()},
        headers=headers,
    )

    # No nodes available
    response = await client.post(
        "/api/v1/clients/provision/",
        json={"external_id": "c2", "protocol": "non-existent"},
        headers=headers,
    )
    assert response.status_code == 503
