from contextlib import asynccontextmanager
from typing import Optional

import httpx


class HTTPClientManager:
    _client: Optional[httpx.AsyncClient] = None

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        if cls._client is None:
            # This should ideally be initialized via lifespan
            # but providing a fallback for tests or unexpected access.
            cls._client = httpx.AsyncClient(
                http2=True,
                timeout=httpx.Timeout(10.0),
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            )
        return cls._client

    @classmethod
    async def close_client(cls):
        if cls._client is not None:
            await cls._client.aclose()
            cls._client = None


@asynccontextmanager
async def http_client_lifespan():
    # Initialize the global client
    client = httpx.AsyncClient(
        http2=True,
        timeout=httpx.Timeout(10.0),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    )
    HTTPClientManager._client = client
    try:
        yield client
    finally:
        await HTTPClientManager.close_client()


async def get_global_httpx_client() -> httpx.AsyncClient:
    return await HTTPClientManager.get_client()
