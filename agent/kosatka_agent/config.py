from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_key: str | None = None
    provider_type: str = "wireguard"  # awg | wireguard | marzban | xray

    # Provider specific settings
    marzban_url: str | None = None
    marzban_username: str | None = None
    marzban_password: str | None = None

    awg_config_path: str = "/etc/amnezia/amneziawg/wg0.conf"
    awg_interface: str = "wg0"
    awg_server_info_path: str = "/opt/kosatka/agent/awg_server.json"
    awg_state_path: str = "/opt/kosatka/agent/awg_peers.json"

    wg_config_path: str = "/etc/wireguard/wg0.conf"
    wg_interface: str = "wg0"
    wg_state_path: str = "/opt/kosatka/agent/wg_peers.json"
    # Written by ansible/roles/wireguard. Separate file so a node can host
    # AWG and vanilla WG side-by-side in the future without key collisions.
    wg_server_info_path: str = "/opt/kosatka/agent/wg_server.json"

    bin_path: str = "/opt/kosatka/bin/"

    # Stealth Chaining settings
    node_role: str = "standalone"  # standalone | proxy | exit
    upstream_address: str | None = None
    relay_uuid: str | None = None
    reality_private_key: str | None = None
    reality_public_key: str | None = None
    reality_short_id: str | None = None
    reality_dest: str = "microsoft.com:443"
    relay_port: int = 443

    # Shaping settings
    shaping_enabled: bool = False
    shaping_total_rate: str = "1gbit"  # Total interface bandwidth

    # Pydantic-settings reads AGENT_*-prefixed env vars so agent.env can cleanly
    # coexist with other services on the same host.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AGENT_",
        extra="ignore",
    )


settings = Settings()
