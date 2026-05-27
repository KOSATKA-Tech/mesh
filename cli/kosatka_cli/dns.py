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
        # domain like relay-1.ub.kosatka.tech
        # Beget needs domain and sub_domain separately
        parts = domain.split(".")
        if len(parts) < 3:
            logger.error(f"Invalid domain format for Beget: {domain}")
            return False

        main_domain = ".".join(parts[-2:])  # kosatka.tech
        sub_domain = ".".join(parts[:-2])  # relay-1.ub

        try:
            # Check if record exists, or just try to add
            # Beget API: dns/add_record
            params = {"fqdn": main_domain, "sub_domain": sub_domain, "type": "A", "value": ip}
            res = await self._request("dns/add_record", params)
            if res.get("status") == "success":
                return True
            logger.error(f"Beget API error: {res}")
            return False
        except Exception as e:
            logger.error(f"Beget API request failed: {e}")
            return False


def get_dns_provider(config: dict) -> DNSProvider:
    provider_type = config.get("dns_provider", "manual")
    if provider_type == "beget":
        return BegetDNSProvider(config["beget_login"], config["beget_api_key"])
    return ManualDNSProvider()
