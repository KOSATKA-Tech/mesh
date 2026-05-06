"""Background job that GeoIPs WG-handshake endpoints into client regions.

Phase 1b's data plane is server-driven: instead of pushing observations
from agent to master (which would require a brand-new agent→master
HTTP path + auth direction), the master *polls* each agent's existing
``GET /clients/{id}/stats`` endpoint, reads the ``endpoint_ip`` field
that Phase 1b adds to the WG/AWG providers, and resolves each IP via
:class:`GeoIPResolver`.

For every client whose detected region differs from what's stored in
``ClientRoutingProfile``:
* If the row is missing → insert (mode defaults to ``smart``).
* If the row exists with ``region_override=True`` → leave it alone
  (the user explicitly chose a region in the bot UI).
* Otherwise → overwrite with the freshly detected value.

Failures are per-client and never cascade: a single dead agent or a
single 429 from ip-api.com only loses that one update.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.client import Client
from ..models.node import Node
from ..models.routing import ClientRoutingProfile
from .geoip_resolver import GeoIPResolver, get_default_resolver

logger = logging.getLogger(__name__)


_DEFAULT_AGENT_TIMEOUT = 5.0


async def _fetch_client_endpoint_ip(
    http: httpx.AsyncClient,
    node: Node,
    external_id: str,
) -> str | None:
    """Hit the agent's ``GET /clients/{external_id}/stats`` and read endpoint_ip.

    Returns ``None`` for any non-success — a stale agent address, an
    auth-key drift, or a client that's never handshaked are all treated
    the same: "no usable observation right now, try again next tick".
    """
    base = (node.address or "").rstrip("/")
    if not base:
        return None
    api_key = node.api_key or settings.effective_agent_api_key()
    url = f"{base}/clients/{external_id}/stats"
    try:
        response = await http.get(
            url,
            headers={"X-Kosatka-Key": api_key},
            timeout=_DEFAULT_AGENT_TIMEOUT,
        )
        if response.status_code != 200:
            return None
        payload: dict[str, Any] = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.debug("agent %s stats fetch failed for %s: %s", node.name, external_id, exc)
        return None
    return payload.get("endpoint_ip")


async def _upsert_region(
    db: AsyncSession,
    client_external_id: str,
    region: str,
) -> bool:
    """Apply a freshly detected ``region`` for ``client_external_id``.

    Returns ``True`` iff the DB row actually changed. ``region_override``
    is the kill switch: a user who picked a region in the bot UI is
    never silently overwritten by a later GeoIP poll.
    """
    result = await db.execute(
        select(ClientRoutingProfile).where(
            ClientRoutingProfile.client_external_id == client_external_id
        )
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        db.add(
            ClientRoutingProfile(
                client_external_id=client_external_id,
                mode="smart",
                region=region,
                region_override=0,
            )
        )
        return True
    if profile.region_override:
        return False
    if profile.region == region:
        return False
    profile.region = region
    return True


async def refresh_client_regions(
    db: AsyncSession,
    *,
    resolver: GeoIPResolver | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, int]:
    """Poll every active client's agent for endpoint_ip and resolve regions.

    Returns a small ``{seen, updated, skipped}`` map for log lines and
    tests. Designed to be cheap to run every few minutes — most clients
    will be cache hits on the resolver after the first pass.
    """
    own_http = http_client is None
    http = http_client or httpx.AsyncClient(timeout=_DEFAULT_AGENT_TIMEOUT)
    resolver = resolver or get_default_resolver()
    counts = {"seen": 0, "updated": 0, "skipped": 0}
    try:
        clients_result = await db.execute(
            select(Client, Node)
            .join(Node, Client.node_id == Node.id)
            .where(Client.is_active.is_(True))
            .where(Node.is_active.is_(True))
        )
        rows = list(clients_result.all())
        # Fetch all endpoints in parallel — the bottleneck is per-agent
        # HTTP latency, not the DB. Single asyncio.gather is bounded by
        # the size of the active-clients table (~100 in MVP).
        ip_lookups = await asyncio.gather(
            *(_fetch_client_endpoint_ip(http, node, client.external_id) for client, node in rows),
            return_exceptions=True,
        )

        for (client, _node), ip in zip(rows, ip_lookups, strict=False):
            counts["seen"] += 1
            if isinstance(ip, Exception) or not ip:
                counts["skipped"] += 1
                continue
            region = await resolver.resolve_region(ip)
            if not region:
                counts["skipped"] += 1
                continue
            changed = await _upsert_region(db, client.external_id, region)
            if changed:
                counts["updated"] += 1
        if counts["updated"]:
            await db.commit()
    finally:
        if own_http:
            await http.aclose()
    logger.info("Region tracker pass: %s", counts)
    return counts
