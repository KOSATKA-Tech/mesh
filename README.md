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
- **Visibility**: Traffic between nodes is indistinguishable from standard HTTPS traffic to trusted domains (e.g., Microsoft, Google).

### 2. Autonomous Agent (Smart Installer)
No more manual `apt-get` or Ansible for every new node.
- **Auto-Detect**: Detects CPU arch (`x86_64`, `arm64`) and OS distribution.
- **Self-Install**: Downloads static binaries or manages Docker sidecars automatically.
- **Kernel-Independent**: Uses `wireguard-go` for userspace VPN if kernel modules are missing.

### 3. Dynamic Node Protection
Protects low-resource (e.g., 512MB RAM / 1-CPU) nodes from being saturated by single users.
- **EMA Smoothing**: Monitors CPU/BW with Exponential Moving Average to ignore transient spikes.
- **Penalty Box**: Active consumers are moved to a throttled class for a short cooling period if the node is under sustained high load.

---

## 🛠 Installation (local development)

```bash
# 1. Clone
git clone https://github.com/6dba/mesh.git
cd mesh

# 2. Create + activate a venv
uv venv
source .venv/bin/activate

# 3. Install the workspace
uv pip install -e .

# 4. Configure & Run
cp .env.master.example .env
kosatka-mesh master run --port 8000
```

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
   *The client gets a config pointing to the Proxy node, but traffic exits through the Exit node.*

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
- [Stealth Chaining Spec](docs/superpowers/specs/2026-05-24-stealth-chaining-auto-install.md)

## ⚖️ License

MIT License.
