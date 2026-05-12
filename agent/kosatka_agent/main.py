import logging

from fastapi import Depends, FastAPI, HTTPException

from .config import settings
from .docs import router as docs_router
from .providers.awg import AmneziaWGProvider
from .providers.base import BaseAgentProvider
from .providers.marzban import MarzbanProvider
from .providers.wireguard import WireGuardProvider
from .providers.xray import XrayProvider
from .security import get_api_key

app = FastAPI(title="Kosatka Mesh Agent")
logger = logging.getLogger(__name__)


def get_provider() -> BaseAgentProvider:
    if settings.provider_type == "wireguard":
        return WireGuardProvider(config_path=settings.wg_config_path)
    elif settings.provider_type == "marzban":
        if not all([settings.marzban_url, settings.marzban_username, settings.marzban_password]):
            raise ValueError("Marzban provider requires url, username and password")
        return MarzbanProvider(
            url=settings.marzban_url,
            username=settings.marzban_username,
            password=settings.marzban_password,
        )
    elif settings.provider_type == "awg":
        return AmneziaWGProvider(config_path=settings.awg_config_path)
    elif settings.provider_type == "xray":
        return XrayProvider()
    else:
        raise ValueError(f"Unknown provider type: {settings.provider_type}")


# Initialize provider
provider = get_provider()


@app.on_event("startup")
async def startup_event():
    logger.info(f"Bootstrapping provider: {settings.provider_type}")
    from .bootstrap import bootstrap_provider

    try:
        await bootstrap_provider(settings.provider_type)
        # For WG/AWG, we also want to ensure the interface is up
        if settings.provider_type in ("wireguard", "awg"):
            if hasattr(provider, "_ensure_server"):
                await provider._ensure_server()
    except Exception as exc:
        logger.error(f"Failed to bootstrap provider {settings.provider_type}: {exc}")


@app.get("/health/")
async def health():
    return {"status": "ok", "provider": settings.provider_type}


# Include documentation router
app.include_router(docs_router)


@app.get("/clients", dependencies=[Depends(get_api_key)])
async def get_clients():
    return await provider.get_clients()


@app.get("/clients/{client_id}", dependencies=[Depends(get_api_key)])
async def get_client(client_id: str):
    client = await provider.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@app.post("/clients", dependencies=[Depends(get_api_key)])
async def create_client(client_data: dict):
    return await provider.create_client(client_data)


@app.delete("/clients/{client_id}", dependencies=[Depends(get_api_key)])
async def delete_client(client_id: str):
    success = await provider.delete_client(client_id)
    if not success:
        raise HTTPException(status_code=404, detail="Client not found or could not be deleted")
    return {"status": "deleted"}


@app.get("/clients/{client_id}/config", dependencies=[Depends(get_api_key)])
async def get_client_config(client_id: str):
    config = await provider.get_client_config(client_id)
    return {"config": config}


@app.get("/clients/{client_id}/stats", dependencies=[Depends(get_api_key)])
async def get_client_stats(client_id: str):
    return await provider.get_client_stats(client_id)
