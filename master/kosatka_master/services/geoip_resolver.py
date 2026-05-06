"""Resolve client IPs to ISO-3166 region codes.

Phase 1b uses this to derive ``ClientRoutingProfile.region`` from the
peer endpoint the agent observed at WireGuard handshake time. Per the
design discussion, region is GeoIP-on-handshake with a sticky manual
override from the bot — the bot's PUT path lives in
``api/v1/routing.py`` (Phase 1a); this module is the auto-detect side.

Provider: ``ip-api.com`` free tier. Reasons:
* No registration / no API key — we don't ship credentials in agent
  configs or org-level secrets.
* 45 req/min/source on the free endpoint, which is plenty for the
  ~100-clients-per-agent scale we're targeting.
* JSON shape is stable; we map ``country`` (ISO-3166 alpha-2) +
  ``region`` (subdivision code) to the ``"<country>-<subdivision>"``
  format the bot already understands.

Caching is in-process with a 24h TTL. Most clients will hit the same
IP for days at a time, so we shouldn't be hammering the upstream API.
On any error we return ``None`` and the caller writes the column as
``NULL`` — that's fine, the routing engine treats unknown region as
"smart, no preference".
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


_DEFAULT_ENDPOINT = "http://ip-api.com/json/{ip}?fields=status,country,countryCode,region"
_DEFAULT_TIMEOUT = 5.0
_DEFAULT_TTL_SECONDS = 24 * 60 * 60


@dataclass
class _CacheEntry:
    region: Optional[str]
    expires_at: float


class GeoIPResolver:
    """Async, in-process, TTL-cached GeoIP lookup.

    A single instance is shared by the scheduler job and any future
    on-demand resolver in API handlers. The lock is per-IP so a flood
    of concurrent lookups for the same IP doesn't stampede the
    upstream API.
    """

    def __init__(
        self,
        *,
        endpoint: str = _DEFAULT_ENDPOINT,
        timeout: float = _DEFAULT_TIMEOUT,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
        http_client: httpx.AsyncClient | None = None,
    ):
        self._endpoint = endpoint
        self._timeout = timeout
        self._ttl = ttl_seconds
        self._cache: dict[str, _CacheEntry] = {}
        # One lock per resolver so concurrent ``resolve_region`` calls
        # for *different* IPs don't serialise. Single lock around cache
        # mutation is fine — the dict update is microsecond-scale.
        self._lock = asyncio.Lock()
        self._client = http_client

    async def _ensure_client(self) -> httpx.AsyncClient:
        # Keep the client alive across lookups; ``ip-api.com`` enforces
        # rate limits per source IP, so HTTP connection reuse is purely
        # a latency optimisation. Created lazily so the importer
        # doesn't have to start an event loop just to instantiate the
        # resolver in tests.
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def resolve_region(self, ip: str) -> Optional[str]:
        """Return ``"<country>-<region>"`` (e.g. ``"RU-MOW"``) or ``None``.

        ``None`` means "we don't know" — caller should leave any
        existing region untouched. Never raises; network errors are
        logged and swallowed.
        """
        if not ip:
            return None
        now = time.monotonic()
        async with self._lock:
            cached = self._cache.get(ip)
            if cached is not None and cached.expires_at > now:
                return cached.region

        region = await self._fetch_region(ip)

        async with self._lock:
            self._cache[ip] = _CacheEntry(region=region, expires_at=now + self._ttl)
        return region

    async def _fetch_region(self, ip: str) -> Optional[str]:
        url = self._endpoint.format(ip=ip)
        try:
            client = await self._ensure_client()
            response = await client.get(url, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("GeoIP lookup for %r failed: %s", ip, exc)
            return None

        if data.get("status") != "success":
            return None
        country = data.get("countryCode")
        region = data.get("region")
        if not country:
            return None
        if region:
            return f"{country}-{region}"
        return country

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# Module-level singleton. The scheduler creates / closes this lazily.
_default_resolver: GeoIPResolver | None = None


def get_default_resolver() -> GeoIPResolver:
    global _default_resolver
    if _default_resolver is None:
        _default_resolver = GeoIPResolver()
    return _default_resolver


async def aclose_default_resolver() -> None:
    global _default_resolver
    if _default_resolver is not None:
        await _default_resolver.aclose()
        _default_resolver = None
