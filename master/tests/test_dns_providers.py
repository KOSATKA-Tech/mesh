import pytest
import respx
from httpx import Response
from kosatka_master.services.dns.providers import (
    BegetProvider,
    CloudflareProvider,
    DigitalOceanProvider,
    HetznerProvider,
    get_dns_provider,
)


@pytest.mark.asyncio
@respx.mock
async def test_cloudflare_provider_create():
    provider = CloudflareProvider(api_token="test-token", zone_id="zone123")
    domain = "node1.test.com"
    ip = "1.2.3.4"

    # Mock search (empty)
    respx.get("https://api.cloudflare.com/client/v4/zones/zone123/dns_records").mock(
        return_value=Response(200, json={"result": []})
    )
    # Mock create
    respx.post("https://api.cloudflare.com/client/v4/zones/zone123/dns_records").mock(
        return_value=Response(200, json={"success": True})
    )

    assert await provider.create_a_record(domain, ip) is True


@pytest.mark.asyncio
@respx.mock
async def test_cloudflare_provider_update():
    provider = CloudflareProvider(api_token="test-token", zone_id="zone123")
    domain = "node1.test.com"
    ip = "1.2.3.4"

    # Mock search (exists)
    respx.get("https://api.cloudflare.com/client/v4/zones/zone123/dns_records").mock(
        return_value=Response(200, json={"result": [{"id": "rec456"}]})
    )
    # Mock update
    respx.put("https://api.cloudflare.com/client/v4/zones/zone123/dns_records/rec456").mock(
        return_value=Response(200, json={"success": True})
    )

    assert await provider.create_a_record(domain, ip) is True


@pytest.mark.asyncio
@respx.mock
async def test_digitalocean_provider():
    provider = DigitalOceanProvider(api_token="test-token")
    domain = "node1.example.com"
    ip = "1.2.3.4"

    respx.get("https://api.digitalocean.com/v2/domains/example.com/records").mock(
        return_value=Response(200, json={"domain_records": []})
    )
    respx.post("https://api.digitalocean.com/v2/domains/example.com/records").mock(
        return_value=Response(201, json={"domain_record": {"id": 1}})
    )

    assert await provider.create_a_record(domain, ip) is True


@pytest.mark.asyncio
@respx.mock
async def test_hetzner_provider():
    provider = HetznerProvider(api_token="test-token")
    domain = "node1.test.de"
    ip = "1.2.3.4"

    respx.get("https://dns.hetzner.com/api/v1/zones").mock(
        return_value=Response(200, json={"zones": [{"id": "z1", "name": "test.de"}]})
    )
    respx.get("https://dns.hetzner.com/api/v1/records").mock(
        return_value=Response(200, json={"records": []})
    )
    respx.post("https://dns.hetzner.com/api/v1/records").mock(return_value=Response(200, json={}))

    assert await provider.create_a_record(domain, ip) is True


@pytest.mark.asyncio
@respx.mock
async def test_beget_provider():
    provider = BegetProvider(login="user", api_key="pass")
    domain = "node1.beget.tech"
    ip = "1.2.3.4"

    respx.get("https://api.beget.com/api/dns/add_record").mock(
        return_value=Response(200, json={"status": "success"})
    )

    assert await provider.create_a_record(domain, ip) is True


def test_get_dns_provider():
    config = {"dns_provider": "cloudflare", "cloudflare_token": "tk", "cloudflare_zone_id": "zi"}
    provider = get_dns_provider(config)
    assert isinstance(provider, CloudflareProvider)

    config = {"dns_provider": "manual"}
    assert get_dns_provider(config) is None
