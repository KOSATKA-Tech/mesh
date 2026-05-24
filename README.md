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

### 1. Stealth Infrastructure & Node Roles
Kosatka Mesh introduces a powerful role-based system for building complex network topologies:

- **`standalone` (Default)**: A standard VPN node. Clients connect directly to this server, and it provides direct internet access.
- **`exit` (Termination)**: A node located in an unrestricted region. It serves as the final "hop" for proxy nodes, receiving obfuscated traffic and routing it to the public internet.
- **`proxy` (Relay)**: A node located in a restricted region. It does **not** provide direct internet access. Instead, it encapsulates client traffic into a stealth tunnel (Xray Reality) and forwards it to a linked `exit` node.

### 2. Autonomous Agent (Smart Installer)
The Agent is designed to be completely self-sufficient:
- **Environment Awareness**: Detects if it's running on a bare host or inside a Docker container.
- **Silent Provisioning**: Automatically downloads and configures the latest stable versions of `xray-core` and `wireguard-go`.
- **Compatibility**: Works across different Linux distributions and CPU architectures (`x86_64`, `arm64`) without manual package installation.

### 3. Dynamic Node Protection
To ensure stability on cheap, low-end VPS:
- **Load Smoothing**: Uses Exponential Moving Average (EMA) to distinguish between transient CPU spikes and sustained overloads.
- **Automated Mitigation**: When a node is saturated, it identifies top-bandwidth consumers and moves them to a throttled queue (Penalty Box) for a cooling period.

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

### Setting up a Stealth Chain (Proxy -> Exit)

Building a stealth bridge requires two nodes with specific roles:

1. **Register the Exit Node**:
   Register a server in an unrestricted region:
   ```bash
   kosatka-mesh nodes add "Global-Exit" "http://exit-ip:8010" --role exit
   ```

2. **Register the Proxy Node**:
   Register a server in a restricted region. The CLI will interactively prompt you to select an available Exit node to link with:
   ```bash
   kosatka-mesh nodes add "Local-Proxy" "http://proxy-ip:8010" --role proxy
   ```

3. **Provision a Stealth Client**:
   Request a configuration for the chained pair:
   ```bash
   kosatka-mesh nodes provision "my-laptop" --protocol "stealth-wg"
   ```
   *The client connects to the **Local-Proxy**, but their traffic is securely tunneled and exits through the **Global-Exit**.*

---

## 📄 Documentation

- [Architecture Overview](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [CLI Reference](docs/cli.md)

## ⚖️ License

MIT License.
