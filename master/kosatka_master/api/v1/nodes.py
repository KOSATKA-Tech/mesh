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

    class Config:
        from_attributes = True


class NodeCreate(BaseModel):
    name: str
    address: str
    provider_type: str = "agent"
    api_key: Optional[str] = None


@router.get("/", response_model=List[NodeSchema])
async def get_nodes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Node))
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
