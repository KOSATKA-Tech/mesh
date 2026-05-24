from unittest.mock import AsyncMock, patch

from kosatka_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_register_node_success():
    with patch("kosatka_cli.nodes.APIClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.register_node = AsyncMock(return_value={"id": 123})

        result = runner.invoke(
            app,
            ["nodes", "register", "MyNode", "1.2.3.4", "--provider", "wireguard"],
        )

        assert result.exit_code == 0
        assert "Successfully registered node 'MyNode' with ID 123" in result.stdout
        # register_node now accepts an optional api_key (defaults to None)
        # so the agent's inbound API token can be registered at the same
        # time as the node row.
        mock_client.register_node.assert_called_once_with(
            "MyNode", "http://1.2.3.4", "wireguard", None
        )


def test_register_node_failure():
    with patch("kosatka_cli.nodes.APIClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.register_node = AsyncMock(side_effect=Exception("API Error"))

        result = runner.invoke(app, ["nodes", "register", "MyNode", "1.2.3.4"])

        assert result.exit_code == 0
        assert "Error registering node: API Error" in result.stdout


def test_node_health_success():
    with patch("kosatka_cli.nodes.APIClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.get_node_health = AsyncMock(return_value={"status": "online", "cpu": 10})

        result = runner.invoke(app, ["nodes", "health", "1"])

        assert result.exit_code == 0
        assert "Health for node 1:" in result.stdout
        assert "online" in result.stdout
        mock_client.get_node_health.assert_called_once_with(1)


def test_node_health_failure():
    with patch("kosatka_cli.nodes.APIClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.get_node_health = AsyncMock(side_effect=Exception("Not Found"))

        result = runner.invoke(app, ["nodes", "health", "999"])

        assert result.exit_code == 0
        assert "Error getting node health: Not Found" in result.stdout
