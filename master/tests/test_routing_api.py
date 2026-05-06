"""End-to-end tests for the smart-routing CRUD + resolver plane.

Cover every method on every endpoint to keep the new module above the
70%-per-module coverage floor we're enforcing for the smart-agent
rollout. The geosite importer's network path is mocked at the
``services.geosite_importer.fetch_tag_recursive`` boundary so these
tests don't need outbound HTTP.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from kosatka_master.config import settings
from kosatka_master.services.geosite_importer import ParsedRow


@pytest.fixture
def auth_headers():
    return {"X-Kosatka-Key": settings.api_key}


@pytest.mark.asyncio
async def test_list_policies_empty_initially(client, auth_headers):
    response = await client.get("/api/v1/policies/", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_policy_returns_201_and_seeds_version(client, auth_headers):
    payload = {
        "name": "ru-default",
        "direct_whitelist": ["*.ru", "192.168.0.0/16"],
        "proxy_blacklist": ["geosite:category-ru-blocked"],
        "max_latency_direct_ms": 150,
        "is_default": True,
    }
    response = await client.post("/api/v1/policies/", json=payload, headers=auth_headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "ru-default"
    assert body["version"] == "1"
    assert body["is_default"] is True
    assert body["direct_whitelist"] == ["*.ru", "192.168.0.0/16"]


@pytest.mark.asyncio
async def test_create_policy_duplicate_name_returns_409(client, auth_headers):
    await client.post("/api/v1/policies/", json={"name": "p1"}, headers=auth_headers)
    response = await client.post("/api/v1/policies/", json={"name": "p1"}, headers=auth_headers)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_creating_second_default_demotes_first(client, auth_headers):
    await client.post(
        "/api/v1/policies/",
        json={"name": "first", "is_default": True},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/policies/",
        json={"name": "second", "is_default": True},
        headers=auth_headers,
    )

    listing = await client.get("/api/v1/policies/", headers=auth_headers)
    by_name = {row["name"]: row for row in listing.json()}
    assert by_name["first"]["is_default"] is False
    assert by_name["second"]["is_default"] is True


@pytest.mark.asyncio
async def test_get_policy_404(client, auth_headers):
    response = await client.get("/api/v1/policies/999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_policy_bumps_version(client, auth_headers):
    create = await client.post("/api/v1/policies/", json={"name": "p"}, headers=auth_headers)
    pid = create.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/policies/{pid}",
        json={"max_latency_direct_ms": 300},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["version"] == "2"
    assert patch_resp.json()["max_latency_direct_ms"] == 300


@pytest.mark.asyncio
async def test_patch_policy_promote_to_default_demotes_others(client, auth_headers):
    a = await client.post(
        "/api/v1/policies/",
        json={"name": "a", "is_default": True},
        headers=auth_headers,
    )
    b = await client.post(
        "/api/v1/policies/",
        json={"name": "b", "is_default": False},
        headers=auth_headers,
    )
    assert a.json()["is_default"] is True
    assert b.json()["is_default"] is False

    promoted = await client.patch(
        f"/api/v1/policies/{b.json()['id']}",
        json={"is_default": True},
        headers=auth_headers,
    )
    assert promoted.json()["is_default"] is True

    refreshed_a = await client.get(f"/api/v1/policies/{a.json()['id']}", headers=auth_headers)
    assert refreshed_a.json()["is_default"] is False


@pytest.mark.asyncio
async def test_delete_default_policy_is_refused(client, auth_headers):
    create = await client.post(
        "/api/v1/policies/",
        json={"name": "p", "is_default": True},
        headers=auth_headers,
    )
    response = await client.delete(f"/api/v1/policies/{create.json()['id']}", headers=auth_headers)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_delete_non_default_policy_succeeds(client, auth_headers):
    create = await client.post("/api/v1/policies/", json={"name": "p"}, headers=auth_headers)
    pid = create.json()["id"]
    response = await client.delete(f"/api/v1/policies/{pid}", headers=auth_headers)
    assert response.status_code == 200
    assert (await client.get(f"/api/v1/policies/{pid}", headers=auth_headers)).status_code == 404


@pytest.mark.asyncio
async def test_unauthorized_calls_are_403(client):
    """Every routing endpoint must require X-Kosatka-Key."""
    for url in (
        "/api/v1/policies/",
        "/api/v1/policies/1",
        "/api/v1/routing/policy",
        "/api/v1/clients/test/routing-profile",
    ):
        response = await client.get(url)
        assert response.status_code == 403, f"{url} leaked without auth header"


@pytest.mark.asyncio
async def test_routing_policy_returns_empty_when_no_default(client, auth_headers):
    """Agent-facing endpoint: never 5xx, even with no policies configured."""
    response = await client.get(
        "/api/v1/routing/policy",
        headers=auth_headers,
        params={"client_id": "tg_user_99"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["policy_version"] == "<empty>"
    assert body["direct_whitelist"] == []
    assert body["proxy_blacklist"] == []
    # Default mode for an unknown client must be "smart" — that's the
    # value the agent assumes when no profile has been written.
    assert body["mode"] == "smart"


@pytest.mark.asyncio
async def test_routing_policy_resolves_default_for_unknown_client(client, auth_headers):
    await client.post(
        "/api/v1/policies/",
        json={
            "name": "default-policy",
            "direct_whitelist": ["*.ru"],
            "proxy_blacklist": ["youtube.com"],
            "is_default": True,
        },
        headers=auth_headers,
    )

    response = await client.get(
        "/api/v1/routing/policy",
        headers=auth_headers,
        params={"client_id": "unknown_user"},
    )
    body = response.json()
    assert body["policy_version"] == "1"
    assert body["direct_whitelist"] == ["*.ru"]
    assert body["proxy_blacklist"] == ["youtube.com"]


@pytest.mark.asyncio
async def test_routing_policy_resolves_per_client_profile(client, auth_headers):
    """A client with an explicit policy_id should *not* see the default."""
    default = await client.post(
        "/api/v1/policies/",
        json={"name": "d", "is_default": True, "direct_whitelist": ["*.ru"]},
        headers=auth_headers,
    )
    custom = await client.post(
        "/api/v1/policies/",
        json={"name": "c", "is_default": False, "direct_whitelist": ["custom.example"]},
        headers=auth_headers,
    )

    # Bind tg_user_42 to the custom policy with always_proxy mode.
    bind = await client.put(
        "/api/v1/clients/tg_user_42/routing-profile",
        json={
            "policy_id": custom.json()["id"],
            "mode": "always_proxy",
            "region": "RU-MOW",
            "region_override": False,
        },
        headers=auth_headers,
    )
    assert bind.status_code == 200, bind.text

    response = await client.get(
        "/api/v1/routing/policy",
        headers=auth_headers,
        params={"client_id": "tg_user_42"},
    )
    body = response.json()
    assert body["policy_version"] == custom.json()["version"]
    assert body["direct_whitelist"] == ["custom.example"]
    assert body["mode"] == "always_proxy"
    assert body["region"] == "RU-MOW"
    # Make sure the default leaked nowhere.
    assert "*.ru" not in body["direct_whitelist"]
    _ = default  # just to silence "unused" lint


@pytest.mark.asyncio
async def test_upsert_client_profile_validates_mode(client, auth_headers):
    response = await client.put(
        "/api/v1/clients/tg_user/routing-profile",
        json={"mode": "fast"},
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upsert_client_profile_validates_policy_id(client, auth_headers):
    response = await client.put(
        "/api/v1/clients/tg_user/routing-profile",
        json={"policy_id": 99999, "mode": "smart"},
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_client_profile_404(client, auth_headers):
    response = await client.get(
        "/api/v1/clients/missing/routing-profile",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_client_profile(client, auth_headers):
    await client.put(
        "/api/v1/clients/tg_user/routing-profile",
        json={"mode": "smart"},
        headers=auth_headers,
    )
    delete_resp = await client.delete(
        "/api/v1/clients/tg_user/routing-profile",
        headers=auth_headers,
    )
    assert delete_resp.status_code == 200
    assert (
        await client.get(
            "/api/v1/clients/tg_user/routing-profile",
            headers=auth_headers,
        )
    ).status_code == 404


@pytest.mark.asyncio
async def test_upsert_client_profile_preserves_user_set_region(client, auth_headers):
    """A user who explicitly chose a region (override=True) shouldn't get
    silently overwritten by the bot's GeoIP-based PUT later on.
    """
    # First write: user picks "RU-SPE" with explicit override.
    await client.put(
        "/api/v1/clients/u1/routing-profile",
        json={"mode": "smart", "region": "RU-SPE", "region_override": True},
        headers=auth_headers,
    )
    # Second write (e.g. bot's auto-GeoIP refresh) without override flag.
    bumped = await client.put(
        "/api/v1/clients/u1/routing-profile",
        json={"mode": "smart", "region": "BY-MIN", "region_override": False},
        headers=auth_headers,
    )
    assert bumped.json()["region"] == "RU-SPE"
    assert bumped.json()["region_override"] is True


@pytest.mark.asyncio
async def test_geosite_import_endpoint_validates_tags(client, auth_headers):
    response = await client.post(
        "/api/v1/policies/import-geosite",
        json={"tags": []},
        headers=auth_headers,
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_geosite_import_records_rows_and_resolver_expands_them(client, auth_headers):
    """Mock the network fetch and verify the importer + resolver loop."""

    async def fake_fetch_recursive(client_, tag, seen=None):
        if tag == "category-ru-blocked":
            return [
                ParsedRow(kind="domain", value="rkn.gov.ru"),
                ParsedRow(kind="keyword", value="censor"),
            ]
        return []

    with patch(
        "kosatka_master.services.geosite_importer.fetch_tag_recursive",
        side_effect=fake_fetch_recursive,
    ):
        # 1. import the tag
        imp = await client.post(
            "/api/v1/policies/import-geosite",
            json={"tags": ["category-ru-blocked"]},
            headers=auth_headers,
        )
        assert imp.status_code == 200
        assert imp.json()["imported"]["category-ru-blocked"] == 2

        # 2. create a default policy that references the tag
        await client.post(
            "/api/v1/policies/",
            json={
                "name": "p",
                "proxy_blacklist": ["geosite:category-ru-blocked", "manual.example"],
                "is_default": True,
            },
            headers=auth_headers,
        )

        # 3. agent-facing resolver should have expanded the geosite ref
        resolved = await client.get(
            "/api/v1/routing/policy",
            headers=auth_headers,
            params={"client_id": "any"},
        )
        body = resolved.json()
        assert "rkn.gov.ru" in body["proxy_blacklist"]
        assert "keyword:censor" in body["proxy_blacklist"]
        assert "manual.example" in body["proxy_blacklist"]
        assert "geosite:category-ru-blocked" not in body["proxy_blacklist"]
