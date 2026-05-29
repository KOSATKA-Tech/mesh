from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from kosatka_master.config import settings
from kosatka_master.database import get_db
from kosatka_master.models.node import Node
from kosatka_master.security import get_api_key
from kosatka_master.services.providers.agent_provider import AgentNodeProvider
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/nodes", tags=["nodes"], dependencies=[Depends(get_api_key)])


class NodeSchema(BaseModel):
    id: int
    name: str
    address: str
    provider_type: str
    status: str
    is_active: bool
    assigned_domain: Optional[str] = None

    model_config = {"from_attributes": True}


class NodeCreate(BaseModel):
    name: str
    address: str
    provider_type: str = "agent"
    api_key: Optional[str] = None


@router.get("/", response_model=List[NodeSchema])
async def get_nodes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node))
    return result.scalars().all()


@router.get("/alerts")
async def get_system_alerts(db: AsyncSession = Depends(get_db)):
    from ...models.alert import SystemAlert

    result = await db.execute(select(SystemAlert).order_by(SystemAlert.created_at.desc()).limit(50))
    return result.scalars().all()


@router.get("/{node_id}", response_model=NodeSchema)
async def get_node(node_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


@router.post("/", response_model=NodeSchema)
async def create_node(node_data: NodeCreate, db: AsyncSession = Depends(get_db)):
    # Upsert semantics so re-running ansible against the same node is
    # idempotent. Without this, the unique constraint on Node.name raises
    # IntegrityError on commit → FastAPI leaks a 500, and the ansible
    # playbook dies on every re-run past the first.
    existing_res = await db.execute(select(Node).where(Node.name == node_data.name))
    existing = existing_res.scalar_one_or_none()
    if existing is not None:
        # Refresh address/provider_type in case the node was rebuilt with a
        # new IP or reprovisioned as a different protocol.
        existing.address = node_data.address
        existing.provider_type = node_data.provider_type
        if node_data.api_key:
            existing.api_key = node_data.api_key
        existing.is_active = True
        await db.commit()
        await db.refresh(existing)
        return existing

    node = Node(**node_data.model_dump())
    db.add(node)
    try:
        await db.commit()
    except IntegrityError as exc:
        # Race: another caller inserted the same name between our SELECT
        # and INSERT. Roll back and resolve by re-reading.
        await db.rollback()
        race_res = await db.execute(select(Node).where(Node.name == node_data.name))
        winner = race_res.scalar_one_or_none()
        if winner is None:
            raise HTTPException(status_code=409, detail=f"Node create conflict: {exc}") from exc
        return winner
    await db.refresh(node)

    # 4. Trigger Automatic DNS registration if configured
    from ...services.dns.dns_service import DNSService

    dns_service = DNSService(db)

    # Extract IP from address (e.g. http://1.2.3.4:8010)
    try:
        from urllib.parse import urlparse

        ip = urlparse(node.address).hostname
        if ip:
            domain = await dns_service.register_node_dns(node.name, ip)
            if domain:
                node.assigned_domain = domain
                await db.commit()
                await db.refresh(node)
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Failed to auto-register DNS for node {node.name}: {e}")

    return node


@router.delete("/{node_id}")
async def delete_node(node_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    await db.delete(node)
    await db.commit()
    return {"status": "success"}


@router.get("/{node_id}/health/")
async def get_node_health(node_id: int, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Probe agent health live. The SDK and CLI both call this endpoint."""
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    key = node.api_key or settings.effective_agent_api_key()
    provider = AgentNodeProvider(key)
    health_data = await provider.sync_node(node.address)

    is_up = health_data is not None
    if is_up:
        node.status = "online"
        if health_data.get("provider"):
            node.provider_type = health_data["provider"]
    else:
        node.status = "offline"

    node.last_seen = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(node)

    return {
        "id": node.id,
        "name": node.name,
        "address": node.address,
        "status": node.status,
        "provider_type": node.provider_type,
    }


@router.get("/{node_id}/host/metrics")
async def get_node_host_metrics(node_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    key = node.api_key or settings.effective_agent_api_key()
    provider = AgentNodeProvider(key)

    # Proxy to Agent's /health/ which contains metrics
    health_data = await provider.sync_node(node.address)
    if not health_data:
        raise HTTPException(status_code=503, detail="Agent unreachable")

    return health_data.get("metrics", {})


@router.post("/{node_id}/host/clean")
async def clean_node_host(node_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    key = node.api_key or settings.effective_agent_api_key()
    headers = {"X-Kosatka-Key": key}

    import httpx

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{node.address.rstrip('/')}/host/clean", headers=headers, timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Failed to trigger cleanup on agent: {e}")


@router.put("/{node_id}/upstreams")
async def set_node_upstreams(
    node_id: int, upstream_ids: list[int], db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Node).where(Node.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    # Validate all upstreams exist
    for uid in upstream_ids:
        if uid == node_id:
            raise HTTPException(status_code=400, detail="Node cannot be its own upstream")
        u_res = await db.execute(select(Node).where(Node.id == uid))
        if not u_res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"Upstream node {uid} not found")

    # Update metadata
    meta = dict(node.metadata_json or {})
    meta["upstreams"] = upstream_ids
    node.metadata_json = meta

    # Also update the primary upstream_id for backward compatibility
    if upstream_ids:
        node.upstream_id = upstream_ids[0]
    else:
        node.upstream_id = None

    await db.commit()

    # Trigger dynamic provisioning
    from kosatka_master.services.chain_manager import ChainManager

    cm = ChainManager(db)
    try:
        await cm.provision_dynamic_relay(node)
    except Exception as e:
        # Don't fail the API call if push fails, but warn the user
        return {
            "status": "partially_updated",
            "warning": f"State saved but failed to push to agent: {e}",
        }

    return {"status": "updated", "upstreams": upstream_ids}
