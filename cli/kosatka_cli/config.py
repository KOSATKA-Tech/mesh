import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

CONFIG_DIR = Path.home() / ".kosatka"
CONFIG_FILE = CONFIG_DIR / "config.json"


class Config(BaseModel):
    base_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    dns_provider: str = "manual"
    base_domain: Optional[str] = None
    cloudflare_token: Optional[str] = None
    cloudflare_zone_id: Optional[str] = None
    do_token: Optional[str] = None
    hetzner_token: Optional[str] = None
    beget_login: Optional[str] = None
    beget_api_key: Optional[str] = None


def load_config() -> Config:
    config = Config()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                config = Config(**data)
        except Exception:
            pass

    if config.base_url and "://" not in config.base_url:
        config.base_url = f"http://{config.base_url}"

    return config


def save_config(config: Config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config.model_dump(), f, indent=2)
