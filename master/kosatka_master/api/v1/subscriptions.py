from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from kosatka_master.database import get_db
from kosatka_master.models.subscription import Subscription
from kosatka_master.security import get_api_key
from kosatka_master.services.subscription_engine import SubscriptionEngine
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/subscriptions", tags=["subscriptions"], dependencies=[Depends(get_api_key)]
)


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
