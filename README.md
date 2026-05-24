# 🐋 KOSATKA Mesh
<div align="center">

![KOSATKA Mesh](./assets/kosatka-mesh.png)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

**KOSATKA Mesh** is a professional-grade centralized control plane for managing a global distributed VPN infrastructure through a unified API. Built for stealth, scalability, and an effortless user experience.

</div>

---

## 🚀 Key Features

- **Unified CLI & API**: Control your entire mesh via the `kosatka-mesh` command or a RESTful API.
- **Universal Subscriptions**: Effortless connection on any device (iOS, Android, Windows, TV) via **Clash-compatible** dynamic configurations.
- **Multi-Hop Stealth Chaining**: Build deep server chains (e.g., `Restricted -> Intermediate -> Exit`) with **Xray Reality** obfuscation.
- **Modern High-Speed Protocols**: Support for **Hysteria2** and **TUIC** (QUIC-based) for lightning-fast performance even on lossy networks.
- **Autonomous Smart Provisioner**: "Zero-touch" installation. The Agent autonomously detects the environment and installs necessary binaries (**sing-box**, WireGuard).
- **Dynamic Traffic Shaping**: Self-protecting nodes. Automatically detects and throttles "heavy hitters" to preserve performance on low-end VPS.
- **Trend-Aware Load Balancing**: Intelligent node selection based on real-time resource utilization trends (CPU/Bandwidth).
- **Protected Analytics Dashboard**: Real-time visualization of the entire network's health and load.

---

## 🏗 Architectural Features

### 1. Universal Connectivity (Clash Subscriptions)
Kosatka Mesh acts as a subscription provider. Each client gets a unique token that provides a dynamic, self-updating configuration compatible with popular apps like **Clash Verge, Stash, Shadowrocket, and Clash Meta**.
- **Smart Naming**: Nodes are automatically labeled with flags and country names (e.g., `🇳🇱 Netherlands [Premium]`).
- **Auto-Selection**: Configurations include "Auto Select" groups that pick the lowest latency node automatically.
- **Privacy**: The client config only sees entry/exit nodes; internal multi-hop topology is fully concealed.

### 2. Unified Transport (Sing-box Core)
We have unified our data plane on the **sing-box** core. A single binary on the agent handles all modern protocols:
- **Hysteria2 / TUIC**: Exceptional performance on mobile networks and unstable links.
- **VLESS + Reality**: State-of-the-art obfuscation that makes VPN traffic indistinguishable from HTTPS to trusted domains.
- **WireGuard**: Industry-standard high-speed VPN in userspace.

### 3. Advanced Stealth Infrastructure
Build arbitrary length server chains to bypass censorship.
- **Multi-Hop**: Direct traffic through multiple jurisdictions before exiting to the internet.
- **Cycle Detection**: The Master node prevents invalid or circular topologies automatically.

---

## 🛠 Installation & Startup

### Local Development (Single-Host)

```bash
# 1. Clone & Setup
git clone https://github.com/6dba/mesh.git && cd mesh
uv venv && source .venv/bin/activate
uv pip install -e .

# 2. Run Master
cp .env.master.example .env
kosatka-mesh master run --port 8000

# 3. Run Agent (in another terminal)
kosatka-mesh agent run --port 8010
```

---

## 🐳 Docker Deployment (Production)

### Master Node Setup
```bash
cp .env.master.example .env.master
$EDITOR .env.master   # set KOSATKA_API_KEY, etc.
docker compose -f docker-compose.master.yml up -d --build
```

### Agent Node Setup
```bash
cp .env.agent.example .env.agent
$EDITOR .env.agent   # set AGENT_API_KEY, KOSATKA_MASTER_URL, etc.
docker compose -f docker-compose.agent.yml up -d --build
```

---

## 📖 Usage Guides

### Getting a Subscription Link

Each client has a subscription token. You can find it in the Master DB or via the CLI (coming soon). The URL format is:
`http://<your-master-ip>:8000/sub/<token>`

Simply paste this link into your favorite Clash-compatible app.

### Setting up a Multi-Hop Chain

1. **Register nodes**:
   ```bash
   # Add Exit Node (EU)
   kosatka-mesh nodes add "Global-Exit" "http://exit-ip:8010" --role exit

   # Add Intermediate Relay (KZ) pointing to EU
   kosatka-mesh nodes add "Mid-Relay" "http://kz-ip:8010" --role proxy --upstream-id <EU_ID>

   # Add Entry Proxy (Local) pointing to KZ
   kosatka-mesh nodes add "Local-Entry" "http://local-ip:8010" --role proxy --upstream-id <MID_ID>
   ```

2. **Provision**:
   ```bash
   kosatka-mesh nodes provision "stealth-user" --protocol "stealth-wg"
   ```

---

## 📦 SDK Integration (e.g., for Telegram Bots)

```python
import asyncio
from KosatkaMesh import MeshClient

async def main():
    client = MeshClient(base_url="https://master.com", api_key="...")

    # 1. Provision a profile
    profile = await client.provision(name="user_1", protocol="hysteria2")

    # 2. Get the universal subscription link for this client
    # (Assuming you have the client object or external_id)
    sub_url = f"https://master.com/sub/{profile.sub_token}"
    print(f"Send this to the user: {sub_url}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📄 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [CLI Reference](docs/cli.md)

## ⚖️ License

MIT License.
