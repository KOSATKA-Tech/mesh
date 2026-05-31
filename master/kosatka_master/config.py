from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Keys are deliberately separate:
    #   api_key       — clients calling the master (SDK, CLI, bot).
    #   agent_api_key — master calling the agent. Must match the value the
    #                   agent reads from AGENT_API_KEY.
    # Defaulting agent_api_key to api_key keeps single-host dev setups
    # working without needing to set both env vars.
    api_key: str = "default-key"
    agent_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./kosatka.db"
    webhook_url: str | None = None
    webhook_secret: str = "default-webhook-secret"

    # SMTP Settings for notifications
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_display_name: str = "Mesh Admin"

    sync_interval: int = 60
    expiration_check_interval: int = 300
    # Geosite re-import cadence. v2fly/domain-list-community lands a few
    # commits a day, so re-pulling every 24h is the right tradeoff
    # between freshness and not hammering the upstream raw.githubusercontent
    # CDN. ``0`` disables the scheduled job (manual ``POST
    # /api/v1/policies/import-geosite`` still works).
    geosite_refresh_interval: int = 86400
    # Default tags to keep refreshed in the background. Empty list ⇒ no
    # automatic refresh; operators add tags as they reference them in
    # policies. Common picks for a Russian-speaking deployment:
    # ``category-ru-blocked``, ``geolocation-!ru``, ``category-ads-all``.
    geosite_default_tags: list[str] = []

    # Bot Integration
    bot_username: str = "KosatkaVPNBot"

    # HTTPS Automation
    domain: str | None = None
    auto_https: bool = False
    serve_ui: bool = True

    def effective_agent_api_key(self) -> str:
        return self.agent_api_key or self.api_key

    model_config = SettingsConfigDict(env_prefix="KOSATKA_", env_file=".env")


settings = Settings()
