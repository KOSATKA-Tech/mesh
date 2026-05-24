import yaml
from kosatka_master.models.client import Client
from kosatka_master.models.node import Node
from kosatka_master.services.subscription_generator import ClashConfigGenerator


def test_clash_generator_filtering():
    """Verify that only 'exit' or 'standalone' active nodes are included."""
    client = Client(sub_token="test-token")

    nodes = [
        Node(
            name="node1",
            address="1.1.1.1",
            role="standalone",
            is_active=True,
            provider_type="wireguard",
            metadata_json={},
        ),
        Node(
            name="node2",
            address="2.2.2.2",
            role="exit",
            is_active=True,
            provider_type="wireguard",
            metadata_json={},
        ),
        Node(
            name="node3",
            address="3.3.3.3",
            role="relay",
            is_active=True,
            provider_type="wireguard",
            metadata_json={},
        ),
        Node(
            name="node4",
            address="4.4.4.4",
            role="standalone",
            is_active=False,
            provider_type="wireguard",
            metadata_json={},
        ),
    ]

    generator = ClashConfigGenerator(client, nodes)
    yaml_output = generator.generate_yaml()
    config = yaml.safe_load(yaml_output)

    proxies = config.get("proxies", [])
    assert len(proxies) == 2
    proxy_names = [p["name"] for p in proxies]
    assert any("node1" in name for name in proxy_names)
    assert any("node2" in name for name in proxy_names)
    assert not any("node3" in name for name in proxy_names)
    assert not any("node4" in name for name in proxy_names)


def test_clash_generator_wireguard_fields():
    """Verify WireGuard proxy entry fields."""
    client = Client(sub_token="test-token")
    node = Node(
        name="wg-node",
        address="wg.example.com",
        role="standalone",
        is_active=True,
        provider_type="wireguard",
        metadata_json={
            "port": 51820,
            "client_ip": "10.0.0.5",
            "client_private_key": "privkey",
            "server_public_key": "pubkey",
            "country_code": "NL",
            "country_name": "Netherlands",
        },
    )

    generator = ClashConfigGenerator(client, [node])
    yaml_output = generator.generate_yaml()
    config = yaml.safe_load(yaml_output)

    proxy = config["proxies"][0]
    assert proxy["type"] == "wireguard"
    assert proxy["server"] == "wg.example.com"
    assert proxy["port"] == 51820
    assert proxy["ip"] == "10.0.0.5"
    assert proxy["private-key"] == "privkey"
    assert proxy["public-key"] == "pubkey"
    assert proxy["udp"] is True
    assert "🇳🇱" in proxy["name"]


def test_clash_generator_vless_reality_fields():
    """Verify VLESS proxy entry fields with REALITY."""
    client = Client(sub_token="test-token")
    node = Node(
        name="vless-node",
        address="vless.example.com",
        role="standalone",
        is_active=True,
        provider_type="vless",
        metadata_json={
            "port": 443,
            "tls": True,
            "reality": True,
            "public_key": "reality-pubkey",
            "short_id": "reality-sid",
            "servername": "google.com",
            "country_code": "US",
            "country_name": "USA",
        },
    )

    generator = ClashConfigGenerator(client, [node])
    yaml_output = generator.generate_yaml()
    config = yaml.safe_load(yaml_output)

    proxy = config["proxies"][0]
    assert proxy["type"] == "vless"
    assert proxy["server"] == "vless.example.com"
    assert proxy["uuid"] == "test-token"
    assert proxy["tls"] is True
    assert proxy["reality-opts"]["public-key"] == "reality-pubkey"
    assert proxy["reality-opts"]["short-id"] == "reality-sid"
    assert "🇺🇸" in proxy["name"]


def test_clash_generator_groups_and_rules():
    """Verify proxy groups and rules are present."""
    client = Client(sub_token="test-token")
    nodes = [
        Node(
            name="n1",
            address="1.1.1.1",
            role="standalone",
            is_active=True,
            provider_type="wireguard",
            metadata_json={},
        ),
    ]

    generator = ClashConfigGenerator(client, nodes)
    yaml_output = generator.generate_yaml()
    config = yaml.safe_load(yaml_output)

    groups = {g["name"]: g for g in config["proxy-groups"]}
    assert "🚀 Auto Select" in groups
    assert groups["🚀 Auto Select"]["type"] == "url-test"
    assert "🛠 Manual Select" in groups
    assert groups["🛠 Manual Select"]["type"] == "select"
    assert "🚀 Auto Select" in groups["🛠 Manual Select"]["proxies"]

    rules = config["rules"]
    assert any("google.com" in r for r in rules)
    assert any("MATCH" in r for r in rules)
