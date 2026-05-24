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
            ["nodes", "register", "MyNode", "1.2.3.4", "--provider", "wireguard", "--role", "exit"],
        )

        assert result.exit_code == 0
        assert "Successfully registered node 'MyNode' with ID 123" in result.stdout
        mock_client.register_node.assert_called_once_with(
            "MyNode", "http://1.2.3.4", "wireguard", None, role="exit", upstream_id=None
        )


def test_register_node_proxy_interactive_success():
    with patch("kosatka_cli.nodes.APIClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.list_nodes = AsyncMock(
            return_value=[{"id": 1, "name": "Exit1", "address": "2.2.2.2"}]
        )
        mock_client.register_node = AsyncMock(return_value={"id": 124})

        # Provide 'proxy' for role and '1' for upstream_id
        result = runner.invoke(
            app,
            ["nodes", "register", "ProxyNode", "1.2.3.4"],
            input="proxy\n1\n",
        )

        assert result.exit_code == 0
        assert "Successfully registered node 'ProxyNode' with ID 124" in result.stdout
        mock_client.list_nodes.assert_called_with(role="exit")
        mock_client.register_node.assert_called_once_with(
            "ProxyNode", "http://1.2.3.4", "agent", None, role="proxy", upstream_id=1
        )


def test_register_node_proxy_no_exit_nodes():
    with patch("kosatka_cli.nodes.APIClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.list_nodes = AsyncMock(return_value=[])

        result = runner.invoke(
            app,
            ["nodes", "register", "ProxyNode", "1.2.3.4", "--role", "proxy"],
        )

        assert result.exit_code == 0
        assert "Error: No Exit nodes available" in result.stdout
        mock_client.register_node.assert_not_called()


def test_register_node_failure():
    with patch("kosatka_cli.nodes.APIClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.register_node = AsyncMock(side_effect=Exception("API Error"))

        result = runner.invoke(
            app, ["nodes", "register", "MyNode", "1.2.3.4", "--role", "standalone"]
        )

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


def test_list_nodes_with_role():
    with patch("kosatka_cli.nodes.APIClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.list_nodes = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "name": "Exit1",
                    "address": "2.2.2.2",
                    "role": "exit",
                    "status": "online",
                    "provider_type": "agent",
                }
            ]
        )

        result = runner.invoke(app, ["nodes", "list", "--role", "exit"])

        assert result.exit_code == 0
        assert "Kosatka Nodes (exit)" in result.stdout
        assert "Exit1" in result.stdout
        mock_client.list_nodes.assert_called_once_with(role="exit")


def test_node_health_failure():
    with patch("kosatka_cli.nodes.APIClient") as mock_client_cls:
        mock_client = mock_client_cls.return_value
        mock_client.get_node_health = AsyncMock(side_effect=Exception("Not Found"))

        result = runner.invoke(app, ["nodes", "health", "999"])

        assert result.exit_code == 0
        assert "Error getting node health: Not Found" in result.stdout
