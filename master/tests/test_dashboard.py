import pytest
from httpx import ASGITransport, AsyncClient
from kosatka_master.config import settings
from kosatka_master.database import Base, engine
from kosatka_master.main import app


@pytest.mark.asyncio
async def test_get_dashboard_html():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/dashboard")
        assert response.status_code == 200
        assert "Kosatka Mesh Dashboard" in response.text
        assert "chart.js" in response.text


@pytest.mark.asyncio
async def test_realtime_stats_endpoint_protected():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # No key
        response = await ac.get("/api/v1/stats/realtime")
        assert response.status_code == 403

        # Valid key
        headers = {"X-Kosatka-Key": settings.api_key}
        response = await ac.get("/api/v1/stats/realtime", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
