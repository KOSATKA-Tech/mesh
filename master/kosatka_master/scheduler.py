import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import settings
from .database import SessionLocal
from .services import geosite_importer, region_tracker
from .services.node_manager import NodeManager
from .services.subscription_engine import SubscriptionEngine

scheduler = AsyncIOScheduler()
logger = logging.getLogger(__name__)


async def sync_nodes_job():
    async with SessionLocal() as db:
        manager = NodeManager(db)
        await manager.sync_all_nodes()


async def check_expirations_job():
    async with SessionLocal() as db:
        engine = SubscriptionEngine(db)
        await engine.check_expirations()


async def refresh_geosite_job():
    """Re-pull configured geosite tags from v2fly/domain-list-community.

    Failures are logged but never raised — a flaky upstream CDN
    shouldn't take the master scheduler loop down.
    """
    if not settings.geosite_default_tags:
        return
    async with SessionLocal() as db:
        try:
            await geosite_importer.import_tags(db, settings.geosite_default_tags)
        except Exception:  # noqa: BLE001 — scheduler must never escape here
            logger.exception("Scheduled geosite refresh failed")


def setup_scheduler():
    scheduler.add_job(sync_nodes_job, "interval", seconds=settings.sync_interval)
    scheduler.add_job(check_expirations_job, "interval", seconds=settings.expiration_check_interval)
    if settings.geosite_refresh_interval > 0 and settings.geosite_default_tags:
        scheduler.add_job(
            refresh_geosite_job,
            "interval",
            seconds=settings.geosite_refresh_interval,
        )
    if settings.region_tracker_interval > 0:
        scheduler.add_job(
            region_tracker_job,
            "interval",
            seconds=settings.region_tracker_interval,
        )
    scheduler.start()


async def region_tracker_job():
    """GeoIP-on-handshake refresh; never raises."""
    async with SessionLocal() as db:
        try:
            await region_tracker.refresh_client_regions(db)
        except Exception:  # noqa: BLE001 — scheduler must never escape here
            logger.exception("Scheduled region tracker pass failed")
