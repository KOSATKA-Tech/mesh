from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from kosatka_agent.main import app


@pytest.fixture
async def client():
    # Use ASGITransport for testing FastAPI app without running a server
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    # Now that we use trailing slashes, /health/ is the canonical URL
    response = await client.get("/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_auth_optional(client):
    # Since we made api_key optional, requests without it should pass if key is not set
    with patch("kosatka_agent.security.settings") as mock_settings:
        mock_settings.api_key = None
        response = await client.get("/clients")
        # Should return 200 (even if empty list) because auth is bypassed
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_required(client):
    # If api_key is set, it should require it
    with patch("kosatka_agent.security.settings") as mock_settings:
        mock_settings.api_key = "secret"
        response = await client.get("/clients")
        assert response.status_code == 403

        headers = {"X-Kosatka-Key": "secret"}
        with patch("kosatka_agent.main.provider") as mock_provider:
            mock_provider.get_clients = AsyncMock(return_value=[])
            response = await client.get("/clients", headers=headers)
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_clients(client):
    with patch("kosatka_agent.main.provider") as mock_provider:
        mock_provider.get_clients = AsyncMock(return_value=[{"id": "test"}])
        response = await client.get("/clients")
        assert response.status_code == 200
        assert response.json() == [{"id": "test"}]


@pytest.mark.asyncio
async def test_create_client(client):
    with patch("kosatka_agent.main.provider") as mock_provider:
        mock_provider.create_client = AsyncMock(return_value={"id": "new", "name": "test"})
        response = await client.post("/clients", json={"name": "test"})
        assert response.status_code == 200
        assert response.json()["id"] == "new"


@pytest.mark.asyncio
async def test_delete_client_success(client):
    with patch("kosatka_agent.main.provider") as mock_provider:
        mock_provider.delete_client = AsyncMock(return_value=True)
        response = await client.delete("/clients/test")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_client(client):
    with patch("kosatka_agent.main.provider") as mock_provider:
        mock_provider.get_client = AsyncMock(return_value={"client_id": "1"})
        response = await client.get("/clients/1")
        assert response.status_code == 200
        assert response.json()["client_id"] == "1"

        mock_provider.get_client = AsyncMock(return_value=None)
        response = await client.get("/clients/2")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_client_config(client):
    with patch("kosatka_agent.main.provider") as mock_provider:
        mock_provider.get_client_config = AsyncMock(return_value="config-text")
        response = await client.get("/clients/1/config")
        assert response.status_code == 200
        assert response.json()["config"] == "config-text"


@pytest.mark.asyncio
async def test_get_client_stats(client):
    with patch("kosatka_agent.main.provider") as mock_provider:
        mock_provider.get_client_stats = AsyncMock(return_value={"rx": 100})
        response = await client.get("/clients/1/stats")
        assert response.status_code == 200
        assert response.json()["rx"] == 100
