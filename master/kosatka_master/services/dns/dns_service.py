import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.alert import SystemConfig
from .providers import get_dns_provider


class DNSService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_config(self) -> dict:
        result = await self.db.execute(select(SystemConfig))
        configs = result.scalars().all()
        obj = {}
        for c in configs:
            try:
                obj[c.key] = json.loads(c.value)
            except:
                obj[c.key] = c.value
        return obj

    async def register_node_dns(self, node_name: str, ip: str) -> str | None:
        """
        Automatically register a DNS record for a node if a provider is configured.
        Returns the full domain if successful, else None.
        """
        config = await self.get_config()
        provider_type = config.get("dns_provider")
        base_domain = config.get("base_domain")

        if not provider_type or not base_domain or provider_type == "manual":
            return None

        provider = get_dns_provider(config)
        if not provider:
            return None

        full_domain = f"{node_name}.{base_domain}"
        success = await provider.create_a_record(full_domain, ip)

        return full_domain if success else None
