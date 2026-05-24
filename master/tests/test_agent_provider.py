import pytest
import respx
from httpx import Response
from kosatka_master.services.providers.agent_provider import AgentNodeProvider


@pytest.mark.asyncio
async def test_agent_provider_sync_node():
    provider = AgentNodeProvider(api_key="secret")
    address = "http://agent:8010"
    
    with respx.mock:
        # Success
        respx.get(f"{address}/health/").mock(
            return_value=Response(200, json={"status": "ok", "provider": "wireguard"})
        )
        res = await provider.sync_node(address)
        assert res["provider"] == "wireguard"
        
        # Failure
        respx.get(f"{address}/health/").mock(
            return_value=Response(500)
        )
        res = await provider.sync_node(address)
        assert res is None


@pytest.mark.asyncio
async def test_agent_provider_no_key():
    provider = AgentNodeProvider(api_key=None)
    address = "http://agent:8010"
    
    with respx.mock:
        route = respx.get(f"{address}/health/").mock(
            return_value=Response(200, json={"status": "ok"})
        )
        await provider.sync_node(address)
        # Check that X-Kosatka-Key was NOT sent
        assert "X-Kosatka-Key" not in route.calls.last.request.headers
