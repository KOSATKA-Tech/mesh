"""Unit tests for the master-side GeoIP resolver."""

from __future__ import annotations

import httpx
import pytest
from kosatka_master.services.geoip_resolver import GeoIPResolver


def _success(country: str, region: str | None = "MOW") -> dict:
    payload: dict = {"status": "success", "countryCode": country}
    if region:
        payload["region"] = region
    return payload


@pytest.mark.asyncio
async def test_resolve_returns_country_region_pair():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_success("RU", "MOW"))

    resolver = GeoIPResolver(http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        assert await resolver.resolve_region("1.2.3.4") == "RU-MOW"
    finally:
        await resolver.aclose()


@pytest.mark.asyncio
async def test_resolve_falls_back_to_country_when_region_missing():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_success("BY", region=None))

    resolver = GeoIPResolver(http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        assert await resolver.resolve_region("5.6.7.8") == "BY"
    finally:
        await resolver.aclose()


@pytest.mark.asyncio
async def test_resolve_returns_none_for_empty_input():
    """Don't make the upstream call when the agent reports no endpoint yet."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_success("RU"))

    resolver = GeoIPResolver(http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        assert await resolver.resolve_region("") is None
    finally:
        await resolver.aclose()
    assert calls == 0


@pytest.mark.asyncio
async def test_resolve_caches_results():
    """Hot path: a busy fleet shouldn't re-query the same IP every tick."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_success("RU", "MOW"))

    resolver = GeoIPResolver(http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        a = await resolver.resolve_region("1.2.3.4")
        b = await resolver.resolve_region("1.2.3.4")
        c = await resolver.resolve_region("1.2.3.4")
    finally:
        await resolver.aclose()
    assert a == b == c == "RU-MOW"
    assert calls == 1


@pytest.mark.asyncio
async def test_failed_lookup_uses_short_negative_ttl_not_24h():
    """A transient 429 must not poison the cache for 24 hours."""
    state = {"calls": 0, "fail": True}

    def handler(request: httpx.Request) -> httpx.Response:
        state["calls"] += 1
        if state["fail"]:
            return httpx.Response(429)
        return httpx.Response(200, json=_success("RU", "MOW"))

    # negative_ttl_seconds=0 ⇒ retry on the very next call.
    resolver = GeoIPResolver(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        negative_ttl_seconds=0,
    )
    try:
        first = await resolver.resolve_region("1.2.3.4")
        assert first is None
        # Upstream "recovers" — the resolver must retry, not return the
        # cached None for the full positive TTL.
        state["fail"] = False
        second = await resolver.resolve_region("1.2.3.4")
    finally:
        await resolver.aclose()
    assert second == "RU-MOW"
    assert state["calls"] == 2


@pytest.mark.asyncio
async def test_resolve_swallows_http_errors():
    """A 429 / 5xx / network error must never propagate to the scheduler."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="Too Many Requests")

    resolver = GeoIPResolver(http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        assert await resolver.resolve_region("1.2.3.4") is None
    finally:
        await resolver.aclose()


@pytest.mark.asyncio
async def test_resolve_returns_none_on_status_fail():
    """ip-api.com signals private/reserved IPs with ``status: fail``."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "fail", "message": "private range"})

    resolver = GeoIPResolver(http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    try:
        assert await resolver.resolve_region("10.0.0.1") is None
    finally:
        await resolver.aclose()


@pytest.mark.asyncio
async def test_cache_expires_after_ttl():
    """Use ttl=0 to force every lookup to re-fetch."""
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_success("RU", "MOW"))

    resolver = GeoIPResolver(
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        ttl_seconds=0,
    )
    try:
        await resolver.resolve_region("1.2.3.4")
        await resolver.resolve_region("1.2.3.4")
    finally:
        await resolver.aclose()
    assert calls == 2
