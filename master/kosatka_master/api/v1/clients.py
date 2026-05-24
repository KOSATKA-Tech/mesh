from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from kosatka_master.config import settings
from kosatka_master.database import get_db
from kosatka_master.models.client import Client
from kosatka_master.models.node import Node
from kosatka_master.security import get_api_key
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/clients", tags=["clients"], dependencies=[Depends(get_api_key)])


class ClientSchema(BaseModel):
    id: int
    external_id: str
    email: str | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ClientCreate(BaseModel):
    external_id: str
    email: str | None = None


class ClientProvisionRequest(BaseModel):
    """Create-or-get a client and materialize a VPN peer on an agent node."""

    external_id: str
    email: Optional[str] = None
    # Which provider family to provision on. Must match Node.provider_type
    # of the agent that will answer (awg | wireguard | marzban | xray).
    protocol: str = "awg"
    # Optional pin to a specific node; otherwise master picks any active
    # node matching `protocol`.
    node_id: Optional[int] = None


class ClientProvisionResponse(BaseModel):
    id: int
    external_id: str
    node_id: int
    provider_type: str
    config_text: str
    address: Optional[str] = None
    public_key: Optional[str] = None


@router.get("/", response_model=List[ClientSchema])
async def get_clients(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client))
    return result.scalars().all()


@router.post("/", response_model=ClientSchema)
async def create_client(client_data: ClientCreate, db: AsyncSession = Depends(get_db)):
    client = Client(**client_data.model_dump())
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientSchema)
async def get_client(client_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.delete("/{client_id}")
async def delete_client(client_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    await db.delete(client)
    await db.commit()
    return {"status": "success"}


async def _pick_node(db: AsyncSession, protocol: str, node_id: Optional[int]) -> Node:
    if node_id is not None:
        # Pinned node_id still has to be active + speaking the right provider;
        # otherwise the agent call later would either time out (inactive) or
        # return a confusing error (sending an AWG payload to a Marzban agent).
        q = await db.execute(select(Node).where(Node.id == node_id, Node.is_active.is_(True)))
        node = q.scalar_one_or_none()
        if node is None:
            raise HTTPException(
                status_code=404,
                detail=f"Node {node_id} not found or inactive",
            )
        if node.provider_type != protocol:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Node {node_id} has provider_type={node.provider_type!r}, "
                    f"cannot serve protocol={protocol!r}"
                ),
            )
        return node

    q = await db.execute(
        select(Node).where(Node.is_active.is_(True), Node.provider_type == protocol).limit(1)
    )
    node = q.scalar_one_or_none()
    if node is None:
        raise HTTPException(
            status_code=503,
            detail=f"No active nodes available for provider_type={protocol!r}",
        )
    return node


async def _call_agent(node: Node, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
    url = f"{node.address.rstrip('/')}{path}"
    # Use the node's specific key if set; fall back to the global key.
    # This allows per-node rotation.
    key = node.api_key or settings.effective_agent_api_key()
    headers = {}
    if key:
        headers["X-Kosatka-Key"] = key

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
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


@router.post("/provision/", response_model=ClientProvisionResponse)
async def provision_client(
    req: ClientProvisionRequest, db: AsyncSession = Depends(get_db)
) -> ClientProvisionResponse:
    """Create-or-get a Client row, pick a node, and ask the agent to
    materialize the peer. Returns the ready-to-import client config."""
    # Idempotent create of the client record.
    existing = await db.execute(select(Client).where(Client.external_id == req.external_id))
    client = existing.scalar_one_or_none()
    if client is None:
        client = Client(external_id=req.external_id, email=req.email)
        db.add(client)
        try:
            await db.commit()
        except IntegrityError:
            # Two concurrent provisions raced on the same external_id; the
            # unique constraint catches the loser. Roll back and pick up the
            # winning row instead of 500-ing.
            await db.rollback()
            race = await db.execute(select(Client).where(Client.external_id == req.external_id))
            client = race.scalar_one()
        else:
            await db.refresh(client)
    elif req.email and client.email != req.email:
        client.email = req.email
        await db.commit()
        await db.refresh(client)

    # Production check: ensure client has an active subscription
    from ...models.subscription import Subscription

    sub_res = await db.execute(
        select(Subscription).where(
            Subscription.client_id == client.id, Subscription.is_active.is_(True)
        )
    )
    if not sub_res.scalar_one_or_none():
        raise HTTPException(
            status_code=403,
            detail=f"Client {req.external_id} has no active subscription. Cannot provision.",
        )

    node = await _pick_node(db, req.protocol, req.node_id)

    agent_payload = {"external_id": req.external_id, "email": req.email}
    agent_result = await _call_agent(node, "POST", "/clients", json=agent_payload)

    # Remember which node materialised the peer so future config/revoke
    # calls can find it without the caller passing node_id.
    if client.node_id != node.id:
        client.node_id = node.id
        await db.commit()
        await db.refresh(client)

    config_text = agent_result.get("config_text") or ""
    if not config_text:
        # Fall back to a dedicated config fetch if the agent returned a bare result.
        try:
            follow_up = await _call_agent(node, "GET", f"/clients/{req.external_id}/config")
            config_text = follow_up.get("config", "") or ""
        except HTTPException:
            config_text = ""

    return ClientProvisionResponse(
        id=client.id,
        external_id=client.external_id,
        node_id=node.id,
        provider_type=node.provider_type,
        config_text=config_text,
        address=agent_result.get("address"),
        public_key=agent_result.get("public_key"),
    )


@router.get("/by-external/{external_id}/config")
async def get_client_config_by_external(
    external_id: str, node_id: Optional[int] = None, db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Proxy to the agent's `/clients/{external_id}/config`.

    Resolution order:
      1. Explicit node_id from the caller (must be active).
      2. node_id persisted on the Client row (set at provision time).
      3. Only-active-node fallback (single-node deployments / legacy rows).
    """
    # 1. Explicit pin
    if node_id is not None:
        q = await db.execute(select(Node).where(Node.id == node_id, Node.is_active.is_(True)))
        node = q.scalar_one_or_none()
        if node is None:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found or inactive")
        return await _call_agent(node, "GET", f"/clients/{external_id}/config")

    # 2. Mapping persisted at provision time
    client_res = await db.execute(select(Client).where(Client.external_id == external_id))
    client = client_res.scalar_one_or_none()
    if client is not None and client.node_id is not None:
        node_res = await db.execute(
            select(Node).where(Node.id == client.node_id, Node.is_active.is_(True))
        )
        node = node_res.scalar_one_or_none()
        if node is not None:
            return await _call_agent(node, "GET", f"/clients/{external_id}/config")
        # else: the originating node is gone/disabled — fall through to
        # best-effort scan rather than 404, the peer might have been
        # migrated or the DB is out-of-sync.

    # 3. Last-resort scan across active nodes. The agent returns an empty
    # config string for unknown peers, so we keep going until one answers.
    active = await db.execute(select(Node).where(Node.is_active.is_(True)))
    for node in active.scalars().all():
        try:
            result = await _call_agent(node, "GET", f"/clients/{external_id}/config")
        except HTTPException:
            continue
        if result.get("config"):
            return result
    raise HTTPException(status_code=404, detail="No node has this client's config")
