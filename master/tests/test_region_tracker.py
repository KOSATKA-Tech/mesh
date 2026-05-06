"""Tests for the periodic GeoIP-on-handshake region tracker."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from kosatka_master.models.client import Client
from kosatka_master.models.node import Node
from kosatka_master.models.routing import ClientRoutingProfile
from kosatka_master.services.geoip_resolver import GeoIPResolver
from kosatka_master.services.region_tracker import refresh_client_regions
from sqlalchemy import select


class _FakeResolver:
    """Stand-in :class:`GeoIPResolver` so tests don't reach the network."""

    def __init__(self, mapping: dict[str, str | None]):
        self.mapping = mapping
        self.calls: list[str] = []

    async def resolve_region(self, ip: str) -> str | None:
        self.calls.append(ip)
        return self.mapping.get(ip)


async def _seed_node_and_client(
    db,
    *,
    node_address: str = "http://agent-1.example",
    external_id: str = "tg_user_1",
) -> tuple[Node, Client]:
    node = Node(name="agent-1", address=node_address, provider_type="agent", is_active=True)
    db.add(node)
    await db.commit()
    await db.refresh(node)
    client = Client(external_id=external_id, is_active=True, node_id=node.id)
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return node, client


def _agent_handler(stats_by_external_id: dict[str, dict[str, Any] | int]):
    """Build a MockTransport handler that mimics agent /clients/{id}/stats.

    Map values can be either a stats dict (200 + JSON) or an int status
    code to simulate non-2xx responses.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        # URL shape: ``http://agent.../clients/<external_id>/stats``
        path = request.url.path
        if not path.startswith("/clients/") or not path.endswith("/stats"):
            return httpx.Response(404)
        external_id = path[len("/clients/") : -len("/stats")]
        value = stats_by_external_id.get(external_id)
        if isinstance(value, int):
            return httpx.Response(value)
        if value is None:
            return httpx.Response(404)
        return httpx.Response(200, json=value)

    return handler


@pytest.mark.asyncio
async def test_refresh_creates_profile_when_missing(db_session):
    _, _ = await _seed_node_and_client(db_session)
    transport = httpx.MockTransport(_agent_handler({"tg_user_1": {"endpoint_ip": "1.2.3.4"}}))
    resolver = _FakeResolver({"1.2.3.4": "RU-MOW"})
    async with httpx.AsyncClient(transport=transport) as http:
        counts = await refresh_client_regions(db_session, resolver=resolver, http_client=http)

    assert counts == {"seen": 1, "updated": 1, "skipped": 0}
    profile = (
        await db_session.execute(
            select(ClientRoutingProfile).where(
                ClientRoutingProfile.client_external_id == "tg_user_1"
            )
        )
    ).scalar_one()
    assert profile.region == "RU-MOW"
    assert profile.region_override == 0
    assert profile.mode == "smart"


@pytest.mark.asyncio
async def test_refresh_updates_existing_profile_when_region_changes(db_session):
    _, _ = await _seed_node_and_client(db_session)
    db_session.add(
        ClientRoutingProfile(
            client_external_id="tg_user_1",
            mode="smart",
            region="RU-MOW",
            region_override=0,
        )
    )
    await db_session.commit()

    transport = httpx.MockTransport(_agent_handler({"tg_user_1": {"endpoint_ip": "9.9.9.9"}}))
    resolver = _FakeResolver({"9.9.9.9": "BY-MIN"})
    async with httpx.AsyncClient(transport=transport) as http:
        counts = await refresh_client_regions(db_session, resolver=resolver, http_client=http)

    assert counts["updated"] == 1
    profile = (
        await db_session.execute(
            select(ClientRoutingProfile).where(
                ClientRoutingProfile.client_external_id == "tg_user_1"
            )
        )
    ).scalar_one()
    assert profile.region == "BY-MIN"


@pytest.mark.asyncio
async def test_refresh_respects_user_override(db_session):
    """region_override=1 means user picked it manually — never overwrite."""
    _, _ = await _seed_node_and_client(db_session)
    db_session.add(
        ClientRoutingProfile(
            client_external_id="tg_user_1",
            mode="smart",
            region="RU-SPE",
            region_override=1,
        )
    )
    await db_session.commit()

    transport = httpx.MockTransport(_agent_handler({"tg_user_1": {"endpoint_ip": "9.9.9.9"}}))
    resolver = _FakeResolver({"9.9.9.9": "BY-MIN"})
    async with httpx.AsyncClient(transport=transport) as http:
        counts = await refresh_client_regions(db_session, resolver=resolver, http_client=http)

    assert counts["updated"] == 0
    profile = (
        await db_session.execute(
            select(ClientRoutingProfile).where(
                ClientRoutingProfile.client_external_id == "tg_user_1"
            )
        )
    ).scalar_one()
    # User-set value preserved; tracker noted "skipped".
    assert profile.region == "RU-SPE"
    assert profile.region_override == 1


@pytest.mark.asyncio
async def test_refresh_skips_clients_without_endpoint_ip(db_session):
    """No endpoint_ip yet (peer never handshaked) ⇒ leave the row alone."""
    _, _ = await _seed_node_and_client(db_session)
    transport = httpx.MockTransport(
        _agent_handler({"tg_user_1": {"endpoint_ip": None, "transfer_rx": 0, "transfer_tx": 0}})
    )
    resolver = _FakeResolver({})
    async with httpx.AsyncClient(transport=transport) as http:
        counts = await refresh_client_regions(db_session, resolver=resolver, http_client=http)

    assert counts == {"seen": 1, "updated": 0, "skipped": 1}
    assert resolver.calls == []


@pytest.mark.asyncio
async def test_refresh_swallows_agent_errors(db_session):
    """A 500 / 404 from one agent must not break other clients in the pass."""
    node1 = Node(name="a1", address="http://a1.example", provider_type="agent", is_active=True)
    node2 = Node(name="a2", address="http://a2.example", provider_type="agent", is_active=True)
    db_session.add_all([node1, node2])
    await db_session.commit()
    await db_session.refresh(node1)
    await db_session.refresh(node2)
    db_session.add_all(
        [
            Client(external_id="alice", is_active=True, node_id=node1.id),
            Client(external_id="bob", is_active=True, node_id=node2.id),
        ]
    )
    await db_session.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        if "alice" in request.url.path:
            return httpx.Response(500)
        return httpx.Response(200, json={"endpoint_ip": "1.2.3.4"})

    transport = httpx.MockTransport(handler)
    resolver = _FakeResolver({"1.2.3.4": "RU-MOW"})
    async with httpx.AsyncClient(transport=transport) as http:
        counts = await refresh_client_regions(db_session, resolver=resolver, http_client=http)

    assert counts == {"seen": 2, "updated": 1, "skipped": 1}
    bob_profile = (
        await db_session.execute(
            select(ClientRoutingProfile).where(ClientRoutingProfile.client_external_id == "bob")
        )
    ).scalar_one()
    assert bob_profile.region == "RU-MOW"


@pytest.mark.asyncio
async def test_refresh_no_active_clients_is_a_noop(db_session):
    counts = await refresh_client_regions(
        db_session,
        resolver=_FakeResolver({}),
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))),
    )
    assert counts == {"seen": 0, "updated": 0, "skipped": 0}


@pytest.mark.asyncio
async def test_refresh_uses_default_resolver_when_none_passed(db_session, monkeypatch):
    """Smoke-coverage of the singleton path; mock at the module boundary."""
    captured: list[str] = []

    class _Captor:
        async def resolve_region(self, ip: str) -> str | None:
            captured.append(ip)
            return "RU-MOW"

    from kosatka_master.services import region_tracker

    monkeypatch.setattr(region_tracker, "get_default_resolver", lambda: _Captor())

    _, _ = await _seed_node_and_client(db_session)
    transport = httpx.MockTransport(_agent_handler({"tg_user_1": {"endpoint_ip": "1.1.1.1"}}))
    async with httpx.AsyncClient(transport=transport) as http:
        await refresh_client_regions(db_session, http_client=http)
    assert captured == ["1.1.1.1"]


def test_geoip_resolver_singleton_imports_cleanly():
    """Sanity: the module-level helper is importable and returns the same instance."""
    from kosatka_master.services.geoip_resolver import aclose_default_resolver, get_default_resolver

    a = get_default_resolver()
    b = get_default_resolver()
    assert a is b
    assert isinstance(a, GeoIPResolver)
    # Best-effort cleanup so the singleton doesn't leak across the test
    # session and tickle the asyncio teardown warnings.
    import asyncio

    asyncio.get_event_loop().run_until_complete(aclose_default_resolver())
