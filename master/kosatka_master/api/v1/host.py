from fastapi import APIRouter, Depends

from ...main import host_monitor
from ...security import get_api_key

router = APIRouter(prefix="/host", tags=["host"])


@router.get("/metrics", dependencies=[Depends(get_api_key)])
async def get_master_host_metrics():
    return host_monitor.get_metrics()


@router.post("/clean", dependencies=[Depends(get_api_key)])
async def clean_master_host():
    await host_monitor.cleanup()
    return {"status": "cleanup_started"}
