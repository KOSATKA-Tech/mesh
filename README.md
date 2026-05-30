# 🐋 KOSATKA Mesh

<div align="center">

![KOSATKA Mesh](./assets/kosatka-mesh.png)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Docker: Ready](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

**Commercial-Grade Global VPN Mesh Infrastructure**

[Visual Dashboard](#-visual-control-plane) • [Security](#-infrastructure-hardening) • [Quick Start](#-quick-start) • [Documentation](#-comprehensive-documentation)

</div>

---

## 🌟 Key Features

*   **Multi-Hop Stealth Chaining**: Build deep server chains (e.g., `Restricted -> Intermediate -> Exit`) with **Xray Reality** to bypass state-level censorship.
*   **Zero-Touch HTTPS**: Integrated **Caddy** automatically provisions Let's Encrypt certificates for Master and all Agents.
*   **Multi-Provider DNS Automation**: Automated A-record management for **Cloudflare, DigitalOcean, Hetzner, and Beget**.
*   **Dynamic Routing & Failover**: Relays automatically detect healthy upstreams and route traffic based on the lowest latency (`leastPing`).
*   **Visual Control Plane**: Interactive Miro-style network graph (PWA) to manage topology with drag-and-drop.
*   **Emergency Access Landing**: A separate [Landing Page](https://github.com/KOSATKA-Tech/kosatka-landing) for onboarding users without VPN via email-based 3-hour trials.
*   **Infrastructure Hardening**: Automated **UFW Firewall**, **Fail2Ban**, and multi-layered **DDoS protection**.
*   **Self-Healing**: Real-time monitoring of CPU, RAM, Disk, and Temp with automated system pruning.

---

## 🎨 Visual Control Plane

Kosatka Mesh features a modern, aesthetic, and fast Admin Panel (PWA) served directly by the Master node.

*   **Network Map**: Drag edges to connect nodes and re-route traffic in real-time.
*   **Fleet Overview**: Health stats (CPU/RAM/Temp) for every node in the mesh.
*   **Mobile Ready**: Fully responsive design with **"Add to Home Screen"** support for iOS and Android.
*   **Configuration**: Centralized management for SMTP, DNS, and Alerting thresholds.

Access it at: `https://master.yourdomain.com/admin/`

---

## 🚀 Quick Start

### 1. Installation
```bash
# Clone and setup CLI
git clone https://github.com/KOSATKA-Tech/mesh.git && cd mesh
uv pip install -e ./cli

# Configure DNS (for automated HTTPS)
kosatka-mesh dns-setup --provider cloudflare --base-domain yourdomain.com
```

### 2. Deployment
```bash
# Register and join a new node "magically" with Auto-HTTPS
# Run this ON THE TARGET SERVER:
kosatka-mesh agent join --master https://master.yourdomain.com --key <API_KEY> --role exit --https
```

---

## 📖 Comprehensive Documentation

| Guide | Description |
| :--- | :--- |
| [**Architecture Overview**](./docs/ARCHITECTURE.md) | Detailed look at how Master, Agents, and Routing work. |
| [**Docker Deployment Guide**](./docs/DOCKER_DEPLOYMENT.md) | Step-by-step setup for Master, Relays, and Exit nodes using Docker. |
| [**CLI Reference**](./docs/cli.md) | Full list of commands for node, host, and DNS management. |
| [**Dynamic Routing Guide**](./docs/ARCHITECTURE.md#5-dynamic-routing) | How to build multi-hop chains and HA clusters. |
| [**Security Policy**](./docs/ARCHITECTURE.md#10-host-security--hardening) | Deep dive into UFW, Fail2Ban, and DDoS protections. |
| [**API Reference**](./docs/api-reference.md) | Technical specs for REST API integration. |

---

## ⚖️ License
MIT License.
_Powered by KOSATKA Tech_ 🦈
