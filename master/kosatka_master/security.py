from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db

api_key_header = APIKeyHeader(name="X-Kosatka-Key", auto_error=False)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

ALGORITHM = "HS256"


async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == settings.api_key:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials",
    )


async def get_current_admin_optional(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.api_key, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None

        from .models.alert import AdminUser

        result = await db.execute(select(AdminUser).where(AdminUser.username == username))
        return result.scalar_one_or_none()
    except JWTError:
        return None


async def validate_operator(
    api_key: str = Security(api_key_header), admin_user=Depends(get_current_admin_optional)
):
    """
    Validates that the caller is either a machine with a valid API Key
    or an authenticated Admin user.
    """
    if api_key == settings.api_key:
        return True
    if admin_user:
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied. Valid API Key or Admin session required.",
    )
