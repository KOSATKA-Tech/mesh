from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from .config import settings

api_key_header = APIKeyHeader(name="X-Kosatka-Key", auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    if not settings.api_key:
        return None
    if api_key_header == settings.api_key:
        return api_key_header
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials",
    )
