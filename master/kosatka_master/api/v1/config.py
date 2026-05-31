import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.alert import SystemConfig
from ...security import validate_operator

router = APIRouter(prefix="/config", tags=["config"], dependencies=[Depends(validate_operator)])


class ConfigUpdate(BaseModel):
    value: str
    description: Optional[str] = None


@router.get("/")
async def get_all_configs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemConfig))
    return result.scalars().all()


@router.get("/{key}")
async def get_config(key: str, db: AsyncSession = Depends(get_db)):
    config = await db.get(SystemConfig, key)
    if not config:
        raise HTTPException(status_code=404, detail="Config key not found")
    return config


@router.put("/{key}")
async def update_config(key: str, data: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    config = await db.get(SystemConfig, key)
    if not config:
        config = SystemConfig(key=key, value=json.dumps(data.get("value")))
        db.add(config)
    else:
        config.value = json.dumps(data.get("value"))

    if "description" in data:
        config.description = data["description"]

    await db.commit()
    return {"status": "updated", "key": key}


@router.post("/batch")
async def update_config_batch(configs: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    for key, value in configs.items():
        config = await db.get(SystemConfig, key)
        if not config:
            config = SystemConfig(key=key, value=json.dumps(value))
            db.add(config)
        else:
            config.value = json.dumps(value)

    await db.commit()
    return {"status": "batch_updated"}
