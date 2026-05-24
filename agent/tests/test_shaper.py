from unittest.mock import AsyncMock, patch

import pytest
from kosatka_agent.shaper import TrafficShaper


@pytest.mark.asyncio
async def test_setup_shaping():
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"", b"")
        mock_exec.return_value = mock_process

        shaper = TrafficShaper("wg0", "1gbit")
        await shaper.setup_shaping()

        # Verify tc commands
        # 1. qdisc del (cleanup)
        # 2. qdisc add root
        # 3. class add root
        # 4. class add throttled
        assert mock_exec.call_count >= 3

        # Check that we have at least one 'add' call
        calls = [args for args, kwargs in mock_exec.call_args_list]
        assert any("add" in call for call in calls)
        assert any("qdisc" in call for call in calls)
        assert any("htb" in call for call in calls)


@pytest.mark.asyncio
async def test_apply_throttle():
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"", b"")
        mock_exec.return_value = mock_process

        shaper = TrafficShaper("wg0", "1gbit")
        await shaper.apply_throttle("10.0.0.2", 5000)

        # Verify tc filter add command
        calls = [args for args, kwargs in mock_exec.call_args_list]
        filter_call = next(c for c in calls if "filter" in c and "add" in c)
        assert "10.0.0.2/32" in filter_call
        assert "1:10" in filter_call


@pytest.mark.asyncio
async def test_remove_throttle():
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"", b"")
        mock_exec.return_value = mock_process

        shaper = TrafficShaper("wg0", "1gbit")
        await shaper.remove_throttle("10.0.0.2")

        # Verify tc filter del command
        calls = [args for args, kwargs in mock_exec.call_args_list]
        filter_call = next(c for c in calls if "filter" in c and "del" in c)
        assert "10.0.0.2/32" in filter_call


@pytest.mark.asyncio
async def test_cleanup_shaping():
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"", b"")
        mock_exec.return_value = mock_process

        shaper = TrafficShaper("wg0", "1gbit")
        await shaper.cleanup_shaping()

        # Verify tc qdisc del command
        calls = [args for args, kwargs in mock_exec.call_args_list]
        assert any("qdisc" in call and "del" in call for call in calls)
