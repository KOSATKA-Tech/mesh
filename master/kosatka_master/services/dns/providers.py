import logging
from abc import ABC, abstractmethod
from typing import Optional

import httpx

logger = logging.getLogger("kosatka.dns")


class DNSProvider(ABC):
    @abstractmethod
    async def create_a_record(self, domain: str, ip: str) -> bool:
        """Create or update an A record."""
        pass


class CloudflareProvider(DNSProvider):
    def __init__(self, api_token: str, zone_id: str):
        self.api_token = api_token
        self.zone_id = zone_id
        self.base_url = "https://api.cloudflare.com/client/v4"

    async def create_a_record(self, domain: str, ip: str) -> bool:
        headers = {"Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json"}
        url = f"{self.base_url}/zones/{self.zone_id}/dns_records"

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, headers=headers, params={"name": domain, "type": "A"})
                resp.raise_for_status()
                records = resp.json().get("result", [])

                payload = {"type": "A", "name": domain, "content": ip, "ttl": 1, "proxied": False}

                if records:
                    await client.put(f"{url}/{records[0]['id']}", headers=headers, json=payload)
                else:
                    await client.post(url, headers=headers, json=payload)
                return True
            except Exception as e:
                logger.error(f"Cloudflare DNS error for {domain}: {e}")
                return False


class DigitalOceanProvider(DNSProvider):
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.digitalocean.com/v2/domains"

    async def create_a_record(self, domain: str, ip: str) -> bool:
        headers = {"Authorization": f"Bearer {self.api_token}"}
        parts = domain.split(".")
        main_domain = ".".join(parts[-2:])
        name = ".".join(parts[:-2])
        url = f"{self.base_url}/{main_domain}/records"

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                records = [
                    r
                    for r in resp.json().get("domain_records", [])
                    if r["name"] == name and r["type"] == "A"
                ]

                if records:
                    await client.put(
                        f"{url}/{records[0]['id']}", headers=headers, json={"data": ip}
                    )
                else:
                    await client.post(
                        url, headers=headers, json={"type": "A", "name": name, "data": ip}
                    )
                return True
            except Exception as e:
                logger.error(f"DigitalOcean DNS error for {domain}: {e}")
                return False


class HetznerProvider(DNSProvider):
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://dns.hetzner.com/api/v1"

    async def create_a_record(self, domain: str, ip: str) -> bool:
        headers = {"Auth-API-Token": self.api_token}
        async with httpx.AsyncClient() as client:
            try:
                zones_resp = await client.get(f"{self.base_url}/zones", headers=headers)
                parts = domain.split(".")
                main_domain = ".".join(parts[-2:])
                zone = next(
                    (
                        z
                        for r in zones_resp.json().get("zones", [])
                        if (z := r)["name"] == main_domain
                    ),
                    None,
                )
                if not zone:
                    return False

                zone_id = zone["id"]
                name = ".".join(parts[:-2])
                records_resp = await client.get(
                    f"{self.base_url}/records", headers=headers, params={"zone_id": zone_id}
                )
                record = next(
                    (
                        r
                        for r in records_resp.json().get("records", [])
                        if r["name"] == name and r["type"] == "A"
                    ),
                    None,
                )

                payload = {"value": ip, "type": "A", "name": name, "zone_id": zone_id}
                if record:
                    await client.put(
                        f"{self.base_url}/records/{record['id']}", headers=headers, json=payload
                    )
                else:
                    await client.post(f"{self.base_url}/records", headers=headers, json=payload)
                return True
            except Exception as e:
                logger.error(f"Hetzner DNS error for {domain}: {e}")
                return False


class Route53Provider(DNSProvider):
    def __init__(self, access_key: str, secret_key: str, hosted_zone_id: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self.hosted_zone_id = hosted_zone_id

    async def create_a_record(self, domain: str, ip: str) -> bool:
        # Placeholder for AWS SDK integration or complex signing
        logger.warning(
            f"Route53 registration for {domain} requested. Please use Cloudflare for full automation."
        )
        return False


class GoogleDNSProvider(DNSProvider):
    def __init__(self, project_id: str, zone_name: str):
        self.project_id = project_id
        self.zone_name = zone_name

    async def create_a_record(self, domain: str, ip: str) -> bool:
        # Placeholder for Google SDK integration
        logger.warning(
            f"Google DNS registration for {domain} requested. Please use Cloudflare for full automation."
        )
        return False


class BegetProvider(DNSProvider):
    def __init__(self, login: str, api_key: str):
        self.login = login
        self.api_key = api_key
        self.base_url = "https://api.beget.com/api"

    async def create_a_record(self, domain: str, ip: str) -> bool:
        parts = domain.split(".")
        main_domain = ".".join(parts[-2:])
        sub_domain = ".".join(parts[:-2])
        params = {
            "login": self.login,
            "passwd": self.api_key,
            "output_format": "json",
            "fqdn": main_domain,
            "sub_domain": sub_domain,
            "type": "A",
            "value": ip,
        }
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/dns/add_record", params=params)
                return resp.json().get("status") == "success"
            except Exception as e:
                logger.error(f"Beget DNS error for {domain}: {e}")
                return False


def get_dns_provider(config: dict) -> Optional[DNSProvider]:
    ptype = config.get("dns_provider")
    if ptype == "cloudflare":
        return CloudflareProvider(config.get("cloudflare_token"), config.get("cloudflare_zone_id"))
    elif ptype == "digitalocean":
        return DigitalOceanProvider(config.get("do_token"))
    elif ptype == "hetzner":
        return HetznerProvider(config.get("hetzner_token"))
    elif ptype == "beget":
        return BegetProvider(config.get("beget_login"), config.get("beget_api_key"))
    elif ptype == "route53":
        return Route53Provider(
            config.get("aws_access_key"), config.get("aws_secret_key"), config.get("aws_zone_id")
        )
    elif ptype == "google":
        return GoogleDNSProvider(config.get("gcp_project_id"), config.get("gcp_zone_name"))
    return None
