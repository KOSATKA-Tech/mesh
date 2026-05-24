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
- **Stealth Chaining**: Seamless **Proxy -> Exit** topology (e.g., RU -> EU) with **Xray Reality** obfuscation to bypass DPI.
- **Autonomous Smart Provisioner**: "Zero-touch" installation. The Agent autonomously detects the environment (Docker/Host) and installs necessary binaries (Xray, WireGuard-go).
- **Dynamic Traffic Shaping**: Self-protecting nodes. Automatically detects and throttles "heavy hitters" to preserve performance on low-end VPS.
- **Trend-Aware Load Balancing**: Intelligent node selection based on real-time resource utilization trends (CPU/Bandwidth).
- **High-Performance Network**: HTTP/2 connection pooling for lightning-fast Master-Agent communication.
- **Provider Abstraction**: Manage AmneziaWG, WireGuard, and VLESS through a single API endpoint.

---

## 🏗 Architectural Features

### 1. Stealth Infrastructure (Phase 2)
Kosatka Mesh supports server-to-server chaining. You can register a node in a restricted region (RU) as a **Proxy** and link it to an **Exit** node in a free region (EU).
- **Transport**: VLESS + Reality (Xray-core).
- **Visibility**: Traffic between nodes is indistinguishable from standard HTTPS traffic to trusted domains (e.g., Microsoft, Google).

### 2. Autonomous Agent (Smart Installer)
No more manual `apt-get` or Ansible for every new node.
- **Auto-Detect**: Detects CPU arch (`x86_64`, `arm64`) and OS distribution.
- **Self-Install**: Downloads static binaries or manages Docker sidecars automatically.
- **Kernel-Independent**: Uses `wireguard-go` for userspace VPN if kernel modules are missing.

### 3. Dynamic Node Protection
Protects 512MB RAM / 1-CPU nodes from being saturated by single users.
- **EMA Smoothing**: Monitors CPU/BW with Exponential Moving Average to ignore transient spikes.
- **Penalty Box**: Active consumers are moved to a throttled class for 2-5 minutes if the node is under sustained high load.

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

### Setting up a Stealth Chain (RU -> EU)

1. **Add the Exit node (EU)**:
   ```bash
   kosatka-mesh nodes add "EU-Exit" "http://eu-ip:8010" --role exit
   ```

2. **Add the Proxy node (RU)**:
   ```bash
   # CLI will interactively ask to pick an Exit node from the list
   kosatka-mesh nodes add "RU-Proxy" "http://ru-ip:8010" --role proxy
   ```

3. **Provision a stealth profile**:
   ```bash
   kosatka-mesh nodes provision "my-stealth-link" --protocol "stealth-wg"
   ```
   *The client gets a config pointing to the RU IP, but traffic exits through the EU node.*

### Enabling Autonomous Shaping

On the Agent host, set the following environment variables:
```bash
AGENT_SHAPING_ENABLED=true
AGENT_SHAPING_TOTAL_RATE=100mbit
```
The agent will now autonomously monitor load and throttle heavy users when CPU > 70%.

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
