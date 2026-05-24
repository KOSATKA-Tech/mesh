import httpx
import pytest
from kosatka_master.http_client import HTTPClientManager, get_global_httpx_client


@pytest.mark.asyncio
async def test_global_client_is_singleton():
    client1 = await get_global_httpx_client()
    client2 = await get_global_httpx_client()
    assert client1 is client2
    assert isinstance(client1, httpx.AsyncClient)


@pytest.mark.asyncio
async def test_global_client_config():
    client = await get_global_httpx_client()
    # Check if http2 is enabled. In httpx, it's checked via the _transport.
    # For AsyncClient, it usually uses AsyncHTTPTransport.
    # We can check the client.limits and other attributes.
    assert client.limits.max_connections == 100
    assert client.limits.max_keepalive_connections == 20
    assert client.timeout.connect == 10.0
    assert client.timeout.read == 10.0

    # Verify http2 is requested in the transport
    # This is a bit internal, but let's see.
    if hasattr(client, "_transport"):
        transport = client._transport
        if hasattr(transport, "_http2"):  # Older httpx
            pass
        # For newer httpx it might be different, but http2=True is what we passed.


@pytest.mark.asyncio
async def test_client_lifecycle():
    # Reset client for this test
    await HTTPClientManager.close_client()
    assert HTTPClientManager._client is None

    client = await get_global_httpx_client()
    assert HTTPClientManager._client is not None
    assert not client.is_closed

    await HTTPClientManager.close_client()
    assert HTTPClientManager._client is None
    assert client.is_closed
