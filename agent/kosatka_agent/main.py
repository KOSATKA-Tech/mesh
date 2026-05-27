import logging
import sys
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException

from .config import settings
from .docs import router as docs_router
from .host_manager import HostManager
from .installer import SmartProvisioner
from .metrics import MetricsCollector
from .protector import HeavyweightProtector
from .providers.awg import AmneziaWGProvider
from .providers.base import BaseAgentProvider
from .providers.marzban import MarzbanProvider
from .providers.singbox import SingboxProvider
from .providers.wireguard import WireGuardProvider
from .providers.xray import XrayProvider
from .providers.xray_relay import XrayRelayProvider
from .security import get_api_key
from .shaper import TrafficShaper

# Configure logging to ensure it shows up in uvicorn
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger("kosatka_agent")


def get_provider() -> BaseAgentProvider:
    if settings.provider_type == "wireguard":
        return WireGuardProvider(config_path=settings.wg_config_path)
    elif settings.provider_type == "marzban":
        return MarzbanProvider(
            url=settings.marzban_url,
            username=settings.marzban_username,
            password=settings.marzban_password,
        )
    elif settings.provider_type == "awg":
        return AmneziaWGProvider(config_path=settings.awg_config_path)
    elif settings.provider_type == "xray":
        return XrayProvider()
    elif settings.provider_type in ("sing-box", "hysteria2", "tuic"):
        return SingboxProvider()
    else:
        raise ValueError(f"Unknown provider type: {settings.provider_type}")


# Initialize provider
provider = get_provider()

# Initialize metrics collector
metrics_collector = MetricsCollector()

# Initialize host manager
host_manager = HostManager()

# Initialize shaper
shaper = TrafficShaper(settings.wg_interface, settings.shaping_total_rate)

# Initialize protector
protector = HeavyweightProtector(shaper, provider, metrics_collector)

# Initialize provisioner
provisioner = SmartProvisioner(bin_path=settings.bin_path)

# Initialize relay provider if needed
relay_provider = None
if settings.node_role in ("proxy", "exit"):
    relay_provider = XrayRelayProvider(settings)


async def _bootstrap_node():
    from .bootstrap import bootstrap_provider

    try:
        await bootstrap_provider(settings.provider_type)
        # For WG/AWG/Sing-box, we also want to ensure the interface/service is up
        if settings.provider_type in ("wireguard", "awg", "sing-box", "hysteria2", "tuic"):
            if hasattr(provider, "_ensure_server"):
                await provider._ensure_server()
            elif hasattr(provider, "_ensure_bootstrapped"):
                await provider._ensure_bootstrapped()
        logger.info("Bootstrapping completed successfully")
    except Exception as exc:
        logger.error(f"Failed to bootstrap provider {settings.provider_type}: {exc}")


async def _startup():
    # Startup logic
    logger.info(f"Starting Kosatka Agent. Provider: {settings.provider_type}")

    # Start host manager
    host_manager.start()

    if relay_provider:
        try:
            await relay_provider.start()
            logger.info(f"Xray Relay started in {settings.node_role} mode")
        except Exception as exc:
            logger.error(f"Failed to start Xray Relay: {exc}")

    # Ensure providers are installed
    try:
        await provisioner.ensure_providers()
    except Exception as exc:
        logger.error(f"Provisioning failed: {exc}")

    # Start metrics collector
    metrics_collector.start()

    # Start shaper and protector if enabled
    if settings.shaping_enabled:
        await shaper.setup_shaping()
        protector.start()

    await _bootstrap_node()


async def _shutdown():
    # Shutdown logic
    logger.info("Kosatka Agent shutting down")
    await host_manager.stop()
    await protector.stop()
    if settings.shaping_enabled:
        await shaper.cleanup_shaping()
    await metrics_collector.stop()
    if relay_provider:
        await relay_provider.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _startup()
    yield
    await _shutdown()


app = FastAPI(title="Kosatka Mesh Agent", lifespan=lifespan)

# Include documentation router
app.include_router(docs_router)


@app.get("/health/")
async def health():
    return {
        "status": "ok",
        "provider": settings.provider_type,
        "metrics": metrics_collector.get_smoothed_metrics(),
    }


@app.post("/host/clean", dependencies=[Depends(get_api_key)])
async def host_clean():
    await host_manager.cleanup()
    return {"status": "cleanup_started"}


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
