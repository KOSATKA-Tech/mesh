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

## 🛠 Installation

```bash
# Clone the repository
git clone https://github.com/6dba/mesh.git
cd mesh

# Create an isolated venv and activate it. ``uv pip install -e .``
# below targets whatever venv is currently active, so skipping these
# two lines installs the editable workspace into the system Python and
# the ``kosatka-mesh`` entrypoint won't appear on PATH.
uv venv
source .venv/bin/activate

# Install in editable mode (installs master, agent, sdk, and cli)
uv pip install -e .

# Copy the example env file and fill in the secrets before running
# ``kosatka-mesh master run`` — the master refuses to start without a
# valid ``KOSATKA_API_KEY``.
cp .env.example .env
```

### Docker (recommended for production)

Two compose files split the deployment between control plane and edge nodes:

```bash
# On the master host (brings up Postgres 16 + master API):
docker compose -f docker-compose.master.yml up -d --build

# On each agent host (registers itself with the master via env vars):
docker compose -f docker-compose.agent.yml up -d --build
```

The master container provisions its own Postgres database with hardcoded
intra-compose credentials — operators only need to supply
``KOSATKA_API_KEY`` and the other application-level settings from
`.env.example`.

---

## 📖 Operational Pipelines

### 1. Bootstrapping the Master Node
The Master is the "brain" of the mesh. It requires an API Key for security.

1. **Configure the Key**: Create a `.env` file in the root or set environment variables:
   ```bash
   export KOSATKA_API_KEY="my-secure-master-key"
   ```
2. **Start Master**:
   ```bash
   kosatka-mesh master run --port 8000
   ```
3. **Login with CLI**:
   ```bash
   kosatka-mesh login my-secure-master-key --base-url http://localhost:8000
   ```

### 2. Setting up a Remote Agent Node
The Agent runs on your VPN servers. It abstracts the underlying VPN software (AmneziaWG, etc.).

1. **Configure Agent**: Set the Agent's local API key (used by Master to talk to Agent):
   ```bash
   export KOSATKA_API_KEY="agent-secret-key"
   ```
2. **Start Agent**:
   ```bash
   kosatka-mesh agent run --port 8010
   ```
3. **Register Node in Master**:
   Tell the Master about this new node:
   ```bash
   kosatka-mesh nodes add --name "Germany-01" --url "http://agent-ip:8010" --key "agent-secret-key"
   ```

### 3. Creating a VPN Profile (Client Provisioning)
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
