# 🐋 KOSATKA Mesh

<div align="center">

![KOSATKA Mesh](./assets/kosatka-mesh.png)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker: Ready](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

**Commercial-Grade Global VPN Mesh Infrastructure**

[Visual Dashboard](#-visual-control-plane) • [Security](#-infrastructure-hardening) • [Quick Start](#-quick-start) • [Documentation](#-comprehensive-documentation)

</div>

---

## 🌟 Key Features

*   **Multi-Hop Stealth Chaining**: Build deep server chains (e.g., `Restricted -> Intermediate -> Exit`) with **Xray Reality** to bypass state-level censorship.
*   **Dynamic Routing & Failover**: Relays automatically detect healthy upstreams and route traffic based on the lowest latency (`leastPing`).
*   **Automated SSL & DNS**: One-click HTTPS provisioning for all nodes via **Beget API** and **Let's Encrypt**.
*   **Visual Control Plane**: Interactive Miro-style network graph to manage topology with drag-and-drop.
*   **Infrastructure Hardening**: Automated **UFW Firewall**, **Fail2Ban**, and multi-layered **DDoS protection**.
*   **Self-Healing**: Real-time monitoring of CPU, RAM, Disk, and Temp with automated system pruning.

---

## 🎨 Visual Control Plane

Kosatka Mesh features a modern, aesthetic, and fast Admin Panel (PWA) served directly by the Master node.

*   **Network Map**: Drag edges to connect nodes and re-route traffic in real-time.
*   **Fleet Overview**: Health stats (CPU/RAM/Temp) for every node in the mesh.
*   **Mobile Ready**: Fully responsive design with **"Add to Home Screen"** support for iOS and Android.
*   **Configuration**: Centralized management for SMTP, DNS, and Alerting thresholds.

Access it at: `https://<your-master-domain>/admin/`

---

## 🛡 Infrastructure Hardening

Security is configured automatically during deployment via Ansible:
- **Default-Deny Firewall**: Only essential ports (SSH, API, VPN) are open.
- **Connection Limiting**: Advanced `iptables` rules protect against handshake exhaustion floods.
- **DDoS Mitigation**: Kernel-level SYN-flood protection and application-level Rate Limiting.
- **Docker Log Rotation**: Prevents disk exhaustion from container logs.

---

## 🚀 Quick Start

### 1. Installation
```bash
# Clone and setup CLI
git clone https://github.com/KOSATKA-Tech/mesh.git && cd mesh
uv pip install -e ./cli

# Configure DNS (for automated HTTPS)
kosatka-mesh dns-setup --provider beget --base-domain yourdomain.com
```

### 2. Deployment
```bash
# Register and join a new node "magically"
# Run this ON THE TARGET SERVER:
kosatka-mesh agent join --master https://master.yourdomain.com --key <API_KEY> --role proxy
```

### 3. Maintenance
```bash
# Check host health across the mesh
kosatka-mesh host status

# Manual system cleanup
kosatka-mesh host clean
```

---

## 📖 Comprehensive Documentation

| Guide | Description |
| :--- | :--- |
| [**Architecture Overview**](./docs/architecture.md) | Detailed look at how Master, Agents, and Routing work. |
| [**CLI Reference**](./docs/cli.md) | Full list of commands for node, host, and DNS management. |
| [**Dynamic Routing Guide**](./docs/architecture.md#5-dynamic-routing) | How to build multi-hop chains and HA clusters. |
| [**Security Policy**](./docs/architecture.md#10-host-security--hardening) | Deep dive into UFW, Fail2Ban, and DDoS protections. |
| [**API Reference**](./docs/api-reference.md) | Technical specs for REST API integration. |
| [**Adding Providers**](./docs/adding-provider.md) | How to add support for new VPN protocols. |

---

## ⚖️ License
MIT License.
_Powered by KOSATKA Infrastructure_ 🦈
