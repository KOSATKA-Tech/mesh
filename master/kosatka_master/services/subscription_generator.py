from typing import Any, Dict, List

import yaml

from ..models.client import Client
from ..models.node import Node


class ClashConfigGenerator:
    """
    Generates Clash-compatible YAML configurations for Kosatka Mesh clients.
    """

    def __init__(self, client: Client, nodes: List[Node]):
        self.client = client
        self.nodes = nodes

    def _get_country_flag(self, country_code: str) -> str:
        """Returns the emoji flag for a given ISO 3166-1 alpha-2 country code."""
        flags = {
            "NL": "🇳🇱",
            "US": "🇺🇸",
            "RU": "🇷🇺",
            "DE": "🇩🇪",
            "FR": "🇫🇷",
            "GB": "🇬🇧",
            "JP": "🇯🇵",
            "SG": "🇸🇬",
            "FI": "🇫🇮",
            "PL": "🇵🇱",
            "TR": "🇹🇷",
        }
        return flags.get(country_code.upper(), "🌐")

    def _get_node_name(self, node: Node) -> str:
        """Generates an intelligent name for the node."""
        country_code = node.metadata_json.get("country_code", "XX")
        flag = self._get_country_flag(country_code)
        country_name = node.metadata_json.get("country_name", "Unknown")
        is_premium = node.metadata_json.get("is_premium", False)
        suffix = " [Premium]" if is_premium else ""
        return f"{flag} {country_name}{suffix} ({node.name})"

    def _build_proxy_entry(self, node: Node) -> Dict[str, Any] | None:
        """Builds a single Clash proxy entry from a Node."""
        name = self._get_node_name(node)

        # Extract server from node.address (strip http/https and paths)
        address = node.address.replace("http://", "").replace("https://", "").split("/")[0]
        if ":" in address:
            server, _ = address.split(":", 1)
        else:
            server = address

        if node.provider_type in ("wireguard", "awg"):
            return {
                "name": name,
                "type": "wireguard",
                "server": server,
                "port": node.metadata_json.get("port", 51820),
                "ip": node.metadata_json.get("client_ip", "10.0.0.2"),
                "private-key": node.metadata_json.get(
                    "client_private_key", "REPLACE_WITH_CLIENT_PRIVATE_KEY"
                ),
                "public-key": node.metadata_json.get(
                    "server_public_key", "REPLACE_WITH_SERVER_PUBLIC_KEY"
                ),
                "pre-shared-key": node.metadata_json.get("preshared_key", ""),
                "udp": True,
            }
        elif node.provider_type in ("vless", "xray", "xray_relay"):
            entry = {
                "name": name,
                "type": "vless",
                "server": server,
                "port": node.metadata_json.get("port", 443),
                "uuid": self.client.sub_token,  # Using sub_token as stable ID
                "cipher": "auto",
                "tls": node.metadata_json.get("tls", True),
                "servername": node.metadata_json.get("servername", server),
                "network": node.metadata_json.get("network", "tcp"),
            }
            if node.metadata_json.get("reality"):
                entry["reality-opts"] = {
                    "public-key": node.metadata_json.get("public_key"),
                    "short-id": node.metadata_json.get("short_id"),
                }
            return entry

        return None

    def generate_yaml(self) -> str:
        """Generates the full Clash YAML configuration."""
        # Filter for 'exit' or 'standalone' nodes only
        endpoints = [n for n in self.nodes if n.role in ("exit", "standalone") and n.is_active]

        proxies = []
        for node in endpoints:
            proxy = self._build_proxy_entry(node)
            if proxy:
                proxies.append(proxy)

        if not proxies:
            # If no proxies found, return a minimal valid Clash config
            return yaml.dump({"proxies": [], "proxy-groups": [], "rules": []})

        proxy_names = [p["name"] for p in proxies]

        config = {
            "port": 7890,
            "socks-port": 7891,
            "allow-lan": True,
            "mode": "rule",
            "log-level": "info",
            "external-controller": "127.0.0.1:9090",
            "proxies": proxies,
            "proxy-groups": [
                {
                    "name": "🚀 Auto Select",
                    "type": "url-test",
                    "proxies": proxy_names,
                    "url": "http://www.gstatic.com/generate_204",
                    "interval": 300,
                    "tolerance": 50,
                },
                {
                    "name": "🛠 Manual Select",
                    "type": "select",
                    "proxies": proxy_names + ["🚀 Auto Select"],
                },
            ],
            "rules": [
                "DOMAIN-SUFFIX,google.com,🚀 Auto Select",
                "GEOIP,LAN,DIRECT",
                "GEOIP,CN,DIRECT",
                "MATCH,🚀 Auto Select",
            ],
        }

        # allow_unicode=True for flags, sort_keys=False to preserve order
        return yaml.dump(config, allow_unicode=True, sort_keys=False)
