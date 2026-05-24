from typing import Any, Dict

import httpx
from fastapi import HTTPException
from kosatka_master.config import settings
from kosatka_master.http_client import get_global_httpx_client
from kosatka_master.models.node import Node


async def call_agent(node: Node, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
    url = f"{node.address.rstrip('/')}{path}"
    # Use the node's specific key if set; fall back to the global key.
    # This allows per-node rotation.
    key = node.api_key or settings.effective_agent_api_key()
    headers = {}
    if key:
        headers["X-Kosatka-Key"] = key

    try:
        client = await get_global_httpx_client()
        resp = await client.request(method, url, headers=headers, **kwargs)
    except httpx.HTTPError as exc:
        # ConnectError / TimeoutException / etc. — translate to a clean 502
        # instead of leaking the raw traceback as a 500.
        raise HTTPException(
            status_code=502,
            detail=f"Agent {node.name!r} unreachable: {exc}",
        ) from exc
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"Agent {node.name} returned {resp.status_code}: {resp.text[:256]}",
        )
    return resp.json()
