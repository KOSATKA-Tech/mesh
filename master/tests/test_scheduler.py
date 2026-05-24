from unittest.mock import AsyncMock, patch

import pytest
from kosatka_master.scheduler import check_expirations_job, sync_nodes_job


@pytest.mark.asyncio
async def test_sync_nodes_job():
    with (
        patch("kosatka_master.scheduler.SessionLocal") as mock_session_cls,
        patch("kosatka_master.scheduler.NodeManager") as mock_manager_cls,
    ):

        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_db

        mock_manager = mock_manager_cls.return_value
        mock_manager.sync_all_nodes = AsyncMock()

        await sync_nodes_job()

        mock_manager_cls.assert_called_once_with(mock_db)
        mock_manager.sync_all_nodes.assert_called_once()


@pytest.mark.asyncio
async def test_check_expirations_job():
    with (
        patch("kosatka_master.scheduler.SessionLocal") as mock_session_cls,
        patch("kosatka_master.scheduler.SubscriptionEngine") as mock_engine_cls,
    ):

        mock_db = AsyncMock()
        mock_session_cls.return_value.__aenter__.return_value = mock_db

        mock_engine = mock_engine_cls.return_value
        mock_engine.check_expirations = AsyncMock()

        await check_expirations_job()

        mock_engine_cls.assert_called_once_with(mock_db)
        mock_engine.check_expirations.assert_called_once()


@pytest.mark.asyncio
async def test_setup_scheduler():
    from kosatka_master.scheduler import setup_scheduler

    with patch("kosatka_master.scheduler.scheduler") as mock_sched:
        setup_scheduler()
        assert mock_sched.add_job.call_count >= 2
        mock_sched.start.assert_called_once()
