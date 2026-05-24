from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from kosatka_cli.api import APIClient


@pytest.fixture
def mock_config():
    with patch("kosatka_cli.api.load_config") as mock_load:
        mock_load.return_value = MagicMock(base_url="http://test.com", api_key="test-key")
        yield mock_load.return_value


@pytest.mark.asyncio
async def test_api_client_request(mock_config):
    client = APIClient()

    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = MagicMock()
        mock_request.return_value = mock_response

        result = await client.request("GET", "/test")

        assert result == {"status": "ok"}
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert args[0] == "GET"
        assert args[1] == "http://test.com/api/v1/test"


@pytest.mark.asyncio
async def test_api_client_list_nodes(mock_config):
    client = APIClient()
    with patch.object(client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = [{"id": 1}]
        nodes = await client.list_nodes()
        assert nodes == [{"id": 1}]
        mock_req.assert_called_once_with("GET", "/nodes", params={})


@pytest.mark.asyncio
async def test_api_client_register_node(mock_config):
    client = APIClient()
    with patch.object(client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"id": 1}
        node = await client.register_node("Node1", "1.1.1.1", "agent")
        assert node == {"id": 1}
        mock_req.assert_called_once_with(
            "POST",
            "/nodes",
            json={
                "name": "Node1",
                "address": "1.1.1.1",
                "provider_type": "agent",
                "api_key": None,
                "role": "standalone",
                "upstream_id": None,
            },
        )


@pytest.mark.asyncio
async def test_api_client_get_node_health(mock_config):
    client = APIClient()
    with patch.object(client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"status": "healthy"}
        health = await client.get_node_health(1)
        assert health == {"status": "healthy"}
        mock_req.assert_called_once_with("GET", "/nodes/1/health")


@pytest.mark.asyncio
async def test_api_client_get_stats(mock_config):
    client = APIClient()
    with patch.object(client, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"total_nodes": 5}
        stats = await client.get_stats()
        assert stats == {"total_nodes": 5}
        mock_req.assert_called_once_with("GET", "/stats/summary")
