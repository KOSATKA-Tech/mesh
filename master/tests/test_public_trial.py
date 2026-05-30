import pytest
import respx
from httpx import Response

@pytest.mark.asyncio
@respx.mock
async def test_request_trial_success(client, db_session):
    from kosatka_master.models.node import Node
    
    # 1. Create an exit node
    node = Node(name="test-exit", address="http://1.2.3.4:8010", provider_type="xray", role="exit")
    db_session.add(node)
    await db_session.commit()

    # 2. Mock Agent response
    respx.post("http://1.2.3.4:8010/clients").mock(
        return_value=Response(200, json={"config_text": "vless://test-config"})
    )

    # 3. Request trial
    response = await client.post("/api/v1/public/trial/request", json={"email": "test@example.com"})
    assert response.status_code == 200
    assert response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_request_trial_invalid_email(client):
    response = await client.post("/api/v1/public/trial/request", json={"email": "not-an-email"})
    assert response.status_code == 422
