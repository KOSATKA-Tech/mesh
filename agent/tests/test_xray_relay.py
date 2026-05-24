from unittest.mock import MagicMock

import pytest
from kosatka_agent.providers.xray_relay import XrayRelayProvider


@pytest.mark.asyncio
async def test_xray_relay_config_exit():
    settings = MagicMock()
    settings.node_role = "exit"
    settings.relay_uuid = "RELAY_UUID"
    settings.reality_private_key = "PRIVATE_KEY"
    settings.reality_short_id = "SHORT_ID"
    settings.reality_dest = "microsoft.com:443"
    settings.relay_port = 443

    provider = XrayRelayProvider(settings)
    config = provider.generate_config()

    assert config["inbounds"][0]["protocol"] == "vless"
    assert config["inbounds"][0]["port"] == 443
    assert config["inbounds"][0]["settings"]["clients"][0]["id"] == "RELAY_UUID"
    assert config["inbounds"][0]["streamSettings"]["security"] == "reality"
    assert config["inbounds"][0]["streamSettings"]["realitySettings"]["privateKey"] == "PRIVATE_KEY"
    assert "SHORT_ID" in config["inbounds"][0]["streamSettings"]["realitySettings"]["shortIds"]


@pytest.mark.asyncio
async def test_xray_relay_config_proxy():
    settings = MagicMock()
    settings.node_role = "proxy"
    settings.upstream_address = "1.2.3.4"
    settings.relay_uuid = "RELAY_UUID"
    settings.reality_public_key = "PUBLIC_KEY"
    settings.reality_short_id = "SHORT_ID"
    settings.relay_port = 443
    settings.reality_dest = "microsoft.com:443"

    provider = XrayRelayProvider(settings)
    config = provider.generate_config()

    # Inbound for local traffic (e.g. Socks)
    assert any(i["protocol"] == "socks" for i in config["inbounds"])

    # Outbound VLESS + Reality
    vless_outbound = next(o for o in config["outbounds"] if o["protocol"] == "vless")
    assert vless_outbound["settings"]["vnext"][0]["address"] == "1.2.3.4"
    assert vless_outbound["settings"]["vnext"][0]["port"] == 443
    assert vless_outbound["settings"]["vnext"][0]["users"][0]["id"] == "RELAY_UUID"
    assert vless_outbound["streamSettings"]["security"] == "reality"
    assert vless_outbound["streamSettings"]["realitySettings"]["publicKey"] == "PUBLIC_KEY"
    assert vless_outbound["streamSettings"]["realitySettings"]["shortId"] == "SHORT_ID"
    assert vless_outbound["streamSettings"]["realitySettings"]["serverName"] == "microsoft.com"
