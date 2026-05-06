# 🐋 KOSATKA Mesh
<div align="center">

![KOSATKA Mesh](./assets/kosatka-mesh.png)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

**KOSATKA Mesh** is a professional-grade centralized control plane for managing a global distributed VPN infrastructure through a unified API.

</div>

---

## 🚀 Key Features

- **Unified CLI**: Control your entire mesh via the `kosatka-mesh` command.
- **Master-Agent Architecture**: Decoupled control plane and execution nodes.
- **Provider Abstraction**: Manage AmneziaWG, WireGuard, and Marzban through a single API endpoint.
- **Capability Autodiscovery**: Master automatically detects what each node can do.
- **One-Command Install**: Simplified workspace setup with `uv`.

---

## 🛠 Installation (local development)

For hacking on the codebase or running a single-host master/agent pair without Docker:

```bash
# 1. Clone
git clone https://github.com/6dba/mesh.git
cd mesh

# 2. Create + activate a venv. Without this step `uv pip install -e .`
#    targets the system Python and the `kosatka-mesh` entrypoint never
#    lands on PATH.
uv venv
source .venv/bin/activate

# 3. Install the workspace (master, agent, sdk, cli).
uv pip install -e .

# 4. Pick the role you're configuring and copy the matching env example.
#    For master:
cp .env.master.example .env
# OR for agent:
# cp .env.agent.example .env

# 5. Edit `.env`, then start the role you copied:
kosatka-mesh master run --port 8000
# OR
# kosatka-mesh agent run --port 8010
```

The master process auto-creates the SQLite parent directory on startup,
so the default `KOSATKA_DATABASE_URL=sqlite+aiosqlite:///./data/kosatka.db`
works out of the box without `mkdir data` first.

---

## 🐋 Docker deployment (recommended for production)

The deployment is split into two compose files — one per role — so a
master host and an agent host configure cleanly without overlapping
variables.

### Master host

```bash
git clone https://github.com/6dba/mesh.git
cd mesh

# Create the master env from the template and fill in the secrets.
cp .env.master.example .env.master
$EDITOR .env.master   # set KOSATKA_API_KEY etc.

# Brings up Postgres 16 + the master API. Postgres credentials are
# hardcoded inside the compose file (this is an internal control-plane
# DB, not exposed to the host network), so operators only need to
# supply application-level settings from .env.master.
docker compose -f docker-compose.master.yml --env-file .env.master \
    up -d --build
```

The master listens on `:8000`. Verify with:

```bash
curl -s http://localhost:8000/health   # → {"status":"ok"}
```

### Agent host

```bash
git clone https://github.com/6dba/mesh.git
cd mesh

cp .env.agent.example .env.agent
$EDITOR .env.agent   # set AGENT_API_KEY, KOSATKA_MASTER_URL, KOSATKA_API_KEY

docker compose -f docker-compose.agent.yml --env-file .env.agent \
    up -d --build
```

The agent listens on `:8010`. Then, from any host that can reach both:

```bash
kosatka-mesh login <master-api-key> --base-url https://your-master-domain
kosatka-mesh nodes add --name "Germany-01" \
    --url "http://<agent-ip>:8010" --key "<agent-api-key>"
```

After registration, the master starts polling the agent's capabilities and you can provision profiles via `kosatka-mesh nodes provision ...`.

---

## 📖 Operational Pipelines

### Creating a VPN Profile (Client Provisioning)
Once the node is registered, creating a VPN profile is seamless. You don't need to know which VPN software is running; the Master handles it.

**Via CLI**:
```bash
# This will find the best node, create a profile, and return the config
kosatka-mesh nodes provision --name "user-laptop" --protocol "amneziawg"
```

**Via Python SDK**:
```python
from KosatkaMesh import MeshClient

client = MeshClient(base_url="http://master-ip:8000", api_key="my-secure-master-key")

# Provision a new client profile on any available node supporting AmneziaWG
profile = await client.provision(
    name="john-doe",
    protocol="amneziawg"
)

print(f"VPN Config: {profile.config_qr_data}")
```

---

## 📦 SDK Integration (e.g., for Telegram Bots)

The `kosatka-sdk` is designed for seamless integration into third-party applications like subscription management bots (e.g., [6dba/mesh](https://github.com/6dba/mesh)).

### Integration Example

Here is how you can manage VPN subscriptions programmatically in your Python project:

```python
import asyncio
from KosatkaMesh import MeshClient

async def main():
    # Initialize the client pointing to your Master Node
    client = MeshClient(
        base_url="https://your-master-domain.com",
        api_key="your-master-admin-key"
    )

    # 1. List available locations (nodes)
    nodes = await client.list_nodes()
    for node in nodes:
        print(f"Node: {node.name} | Load: {node.current_clients}/{node.max_clients}")

    # 2. Provision a new VPN profile
    # This automatically selects the best available node supporting the protocol
    profile = await client.provision(
        name="user_12345",
        protocol="amneziawg"
    )

    print(f"Profile created on Node ID: {profile.node_id}")
    print(f"VPN Config:\n{profile.config_text}")

    # 3. Revoke access
    await client.revoke(profile.client_id)

if __name__ == "__main__":
    asyncio.run(main())
```

### Webhook Handling

For real-time updates (e.g., notifying a user when their subscription is about to expire), you can use the built-in webhook utility:

```python
from KosatkaMesh.webhook import KosatkaWebhookHandler

webhook = KosatkaWebhookHandler(secret="your-webhook-secret")

@webhook.on("subscription_expired")
async def handle_expiry(event):
    # event.data contains the metadata you provided during provisioning
    external_id = event.data.get("external_id")
    print(f"Notifying user {external_id} that their access was revoked.")
```

---

## 🏗 Supported VPN Providers

KOSATKA Mesh can manage the following services on any node:
- **AmneziaWG**: Modern, obfuscated WireGuard fork.
- **WireGuard**: Industry standard high-performance VPN.
- **Marzban**: Powerful proxy management for Xray/VLESS/VMess.

To add a new VPN service to a node, simply install it and configure the Agent to point to its configuration path or API.

---

## 📄 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [CLI Reference](docs/cli.md)

## ⚖️ License

MIT License.
