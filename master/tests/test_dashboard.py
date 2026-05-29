import pytest

@pytest.mark.asyncio
async def test_get_dashboard_html(client):
    response = await client.get("/dashboard")
    assert response.status_code == 200
    assert "Kosatka Mesh Dashboard" in response.text
    assert "chart.js" in response.text


@pytest.mark.asyncio
async def test_realtime_stats_endpoint_protected(client):
    from kosatka_master.config import settings
    
    # No key
    response = await client.get("/api/v1/stats/realtime")
    assert response.status_code == 403

    # Valid key
    headers = {"X-Kosatka-Key": settings.api_key}
    response = await client.get("/api/v1/stats/realtime", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
