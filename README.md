# 🐋 KOSATKA Mesh
<div align="center">

![KOSATKA Mesh](./assets/kosatka-mesh.png)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

**KOSATKA Mesh** is a professional-grade centralized control plane for managing a global distributed VPN infrastructure through a unified API. Built for stealth, scalability, and extreme ease of use.

</div>

---

## 🚀 Key Features

- **Unified CLI**: Control your entire mesh via the `kosatka-mesh` command.
- **Stealth Chaining**: Seamless **Proxy -> Exit** topology with **Xray Reality** obfuscation to bypass DPI and censorship.
- **Autonomous Smart Provisioner**: "Zero-touch" installation. The Agent autonomously detects the environment (Docker/Host) and installs necessary binaries (Xray, WireGuard-go).
- **Dynamic Traffic Shaping**: Self-protecting nodes. Automatically detects and throttles "heavy hitters" to preserve performance on low-end VPS.
- **Trend-Aware Load Balancing**: Intelligent node selection based on real-time resource utilization trends (CPU/Bandwidth).
- **High-Performance Network**: HTTP/2 connection pooling for lightning-fast Master-Agent communication.
- **Provider Abstraction**: Manage AmneziaWG, WireGuard, and VLESS through a single API endpoint.

---

## 🏗 Architectural Features

### 1. Stealth Infrastructure
Kosatka Mesh supports server-to-server chaining. You can register a node in a restricted region as a **Proxy** and link it to an **Exit** node in an unrestricted region.
- **Transport**: VLESS + Reality (Xray-core).
- **Visibility**: Traffic between nodes is indistinguishable from standard HTTPS traffic to trusted domains.

### 2. Autonomous Agent (Smart Installer)
No more manual `apt-get` or Ansible for every new node.
- **Auto-Detect**: Detects CPU arch (`x86_64`, `arm64`) and OS distribution.
- **Self-Install**: Downloads static binaries or manages Docker sidecars automatically.
- **Kernel-Independent**: Uses `wireguard-go` for userspace VPN if kernel modules are missing.

---

## 🛠 Installation & Startup

### Local Development (Single-Host)

For hacking on the codebase or running a local master/agent pair:

```bash
# 1. Clone & Setup
git clone https://github.com/6dba/mesh.git && cd mesh
uv venv && source .venv/bin/activate
uv pip install -e .

# 2. Run Master
cp .env.master.example .env
kosatka-mesh master run --port 8000

# 3. Run Agent (in another terminal)
# cp .env.agent.example .env
kosatka-mesh agent run --port 8010
```

---

## 🐳 Docker Deployment (Production)

The deployment is split into two compose files—one per role—so a master host and an agent host configure cleanly.

### Master Node Setup

```bash
# Create master env and fill in secrets
cp .env.master.example .env.master
$EDITOR .env.master   # set KOSATKA_API_KEY, etc.

# Bring up Postgres 16 + Master API
docker compose -f docker-compose.master.yml up -d --build
```
*Master listens on `:8000`. Verify with `curl http://localhost:8000/health`.*

### Agent Node Setup

```bash
cp .env.agent.example .env.agent
$EDITOR .env.agent   # set AGENT_API_KEY, KOSATKA_MASTER_URL, etc.

# Bring up the Agent
docker compose -f docker-compose.agent.yml up -d --build
```
> [!IMPORTANT]
> To manage VPN interfaces, the Docker container needs **NET_ADMIN** capabilities (included in the default compose file).

---

## 📖 Usage Guides

### Setting up a Stealth Chain

1. **Add the Exit node**:
   ```bash
   kosatka-mesh nodes add "Exit-Node" "http://exit-ip:8010" --role exit
   ```

2. **Add the Proxy node**:
   ```bash
   # CLI will interactively ask to pick an Exit node from the list
   kosatka-mesh nodes add "Proxy-Node" "http://proxy-ip:8010" --role proxy
   ```

3. **Provision a stealth profile**:
   ```bash
   kosatka-mesh nodes provision "stealth-user" --protocol "stealth-wg"
   ```

### Enabling Autonomous Shaping

On the Agent host, set the following environment variables:
```bash
AGENT_SHAPING_ENABLED=true
AGENT_SHAPING_TOTAL_RATE=100mbit
```
The agent will now autonomously monitor load and throttle heavy users when sustained load is detected.

---

## 📦 SDK Integration

```python
from KosatkaMesh import MeshClient

client = MeshClient(base_url="https://master.com", api_key="...")

# Provision a profile with automatic trend-aware balancing
profile = await client.provision(name="user1", protocol="amneziawg")
```

---

## 📄 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [CLI Reference](docs/cli.md)

## ⚖️ License

MIT License.
