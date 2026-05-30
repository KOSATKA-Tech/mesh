import logging

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...services.trial import TrialService
from .limiter import limiter

router = APIRouter(prefix="/public", tags=["public"])
logger = logging.getLogger("kosatka_master.api.public")


class TrialRequest(BaseModel):
    email: EmailStr


@router.post("/trial/request")
@limiter.limit("1 per 10 minutes")
async def request_trial(request: Request, req: TrialRequest, db: AsyncSession = Depends(get_db)):
    """
    Public endpoint to request a 3-hour emergency access.
    """
    service = TrialService(db)
    success = await service.request_trial(req.email)

    if not success:
        # We don't reveal too much info to prevent enumeration
        return {
            "status": "error",
            "message": "Could not process request. Please try again later or check if you already have an account.",
        }

    return {"status": "success", "message": "Emergency access granted. Check your email."}


@router.get("/health")
async def public_health():
    return {"status": "ok"}
