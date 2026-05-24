from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response
from kosatka_master.database import get_db
from kosatka_master.models.client import Client
from kosatka_master.models.node import Node
from kosatka_master.models.subscription import Subscription
from kosatka_master.security import get_api_key
from kosatka_master.services.subscription_engine import SubscriptionEngine
from kosatka_master.services.subscription_generator import ClashConfigGenerator
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/subscriptions", tags=["subscriptions"], dependencies=[Depends(get_api_key)]
)

public_router = APIRouter(tags=["subscriptions-public"])


class SubscriptionSchema(BaseModel):
    id: int
    client_id: int
    plan_name: str
    expires_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    client_id: int
    plan_name: str
    expires_at: datetime


@router.get("/", response_model=List[SubscriptionSchema])
async def get_subscriptions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subscription))
    return result.scalars().all()


@router.post("/", response_model=SubscriptionSchema)
async def create_subscription(sub_data: SubscriptionCreate, db: AsyncSession = Depends(get_db)):
    engine = SubscriptionEngine(db)
    sub = await engine.create_subscription(
        client_id=sub_data.client_id, plan_name=sub_data.plan_name, expires_at=sub_data.expires_at
    )
    return sub


@router.get("/client/{client_id}", response_model=List[SubscriptionSchema])
async def get_client_subscriptions(client_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subscription).where(Subscription.client_id == client_id))
    return result.scalars().all()


@public_router.get("/{token}")
async def get_subscription(token: str, db: AsyncSession = Depends(get_db)):
    """
    Public endpoint for serving client subscriptions in Clash YAML format.
    """
    # 1. Query Client where sub_token == token and sub_enabled is True
    result = await db.execute(
        select(Client).where(Client.sub_token == token, Client.sub_enabled.is_(True))
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Subscription not found or disabled")

    # 2. Query all active nodes
    nodes_result = await db.execute(select(Node).where(Node.is_active.is_(True)))
    nodes = nodes_result.scalars().all()

    # 3. Generate YAML using ClashConfigGenerator
    generator = ClashConfigGenerator(client, list(nodes))
    yaml_content = generator.generate_yaml()

    # 4. Return Response with headers
    return Response(
        content=yaml_content,
        media_type="application/x-yaml; charset=utf-8",
        headers={
            "subscription-userinfo": "upload=0;download=0;total=1000000000000;expire=0",
            "profile-update-interval": "24",
        },
    )
