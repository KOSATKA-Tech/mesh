import logging
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger("kosatka_cli.dns")


class DNSProvider(ABC):
    @abstractmethod
    async def create_a_record(self, domain: str, ip: str) -> bool:
        """Create an A record for the given domain pointing to the IP."""
        pass


class ManualDNSProvider(DNSProvider):
    async def create_a_record(self, domain: str, ip: str) -> bool:
        print("\n[bold yellow]ACTION REQUIRED:[/bold yellow]")
        print("Please create an A record manually:")
        print(f"  Domain: [cyan]{domain}[/cyan]")
        print(f"  Target IP: [green]{ip}[/green]")
        input("\nPress Enter once you have created the record...")
        return True


class CloudflareDNSProvider(DNSProvider):
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
                if records:
                    await client.put(
                        f"{url}/{records[0]['id']}",
                        headers=headers,
                        json={
                            "type": "A",
                            "name": domain,
                            "content": ip,
                            "ttl": 1,
                            "proxied": False,
                        },
                    )
                else:
                    await client.post(
                        url,
                        headers=headers,
                        json={
                            "type": "A",
                            "name": domain,
                            "content": ip,
                            "ttl": 1,
                            "proxied": False,
                        },
                    )
                return True
            except Exception as e:
                logger.error(f"Cloudflare DNS error: {e}")
                return False


class BegetDNSProvider(DNSProvider):
    def __init__(self, login: str, api_key: str):
        self.login = login
        self.api_key = api_key
        self.base_url = "https://api.beget.com/api"

    async def _request(self, method: str, params: dict):
        url = f"{self.base_url}/{method}"
        params.update({"login": self.login, "passwd": self.api_key, "output_format": "json"})
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    async def create_a_record(self, domain: str, ip: str) -> bool:
        parts = domain.split(".")
        if len(parts) < 3:
            logger.error(f"Invalid domain format for Beget: {domain}")
            return False

        main_domain = ".".join(parts[-2:])
        sub_domain = ".".join(parts[:-2])

        try:
            params = {"fqdn": main_domain, "sub_domain": sub_domain, "type": "A", "value": ip}
            res = await self._request("dns/add_record", params)
            return res.get("status") == "success"
        except Exception as e:
            logger.error(f"Beget API request failed: {e}")
            return False


def get_dns_provider(config: dict) -> DNSProvider:
    provider_type = config.get("dns_provider", "manual")
    if provider_type == "beget":
        return BegetDNSProvider(config["beget_login"], config["beget_api_key"])
    elif provider_type == "cloudflare":
        return CloudflareDNSProvider(config["cloudflare_token"], config["cloudflare_zone_id"])
    return ManualDNSProvider()
