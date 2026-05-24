# Design Spec: Stealth Chaining & Smart Provisioning (Phase 2)

**Date:** 2026-05-24
**Status:** Approved
**Goal:** Implement server chaining (Proxy -> Exit) for traffic obfuscation and autonomous "zero-touch" VPN provider installation on Agents.

---

## 1. Node Roles & Topology (Master)
To support stealth infrastructure, we introduce explicit node roles and a chaining relationship.

### 1.1. Roles
- **Standalone:** Standard VPN server (Direct client-to-server).
- **Proxy:** Relay node (e.g., in RU) that forwards traffic to an Exit node. Does not terminate VPN connections to the internet.
- **Exit:** Termination node (e.g., in EU) that receives traffic from Proxy nodes and routes it to the public internet.

### 1.2. Interactive Registration (CLI)
- `kosatka-mesh nodes add` will interactively prompt for a role if `--role` is not provided.
- If `Proxy` is selected, the CLI will query the Master for available `Exit` nodes and allow interactive selection.
- Detailed help descriptions for each role will be added to the CLI.

---

## 2. Stealth Chaining (Xray Reality)
Traffic between Proxy and Exit nodes must be obfuscated to bypass DPI.

### 2.1. Mechanism
- **Transport:** Xray-core with **VLESS + Reality** protocol.
- **Proxy Node:** Acts as a Reality client, establishing a tunnel to the Exit node.
- **Exit Node:** Acts as a Reality server, masking the tunnel as legitimate HTTPS traffic (e.g., disguised as `microsoft.com`).
- **Encapsulation:** All client protocols (WireGuard, AmneziaWG) are encapsulated within this stealth tunnel between nodes.

---

## 3. Smart Provisioner (Agent Auto-Installation)
The Agent becomes responsible for its own environment setup, supporting both Docker and Host-native modes.

### 3.1. Environment Detection
- **Docker-in-Docker (DinD) Aware:** If the Agent detects it is running inside a container, it will attempt to use sidecar containers or embedded binaries depending on the Docker socket availability.
- **Host Mode:** If no Docker is available, the Agent detects CPU architecture (`x86_64`, `arm64`) and OS distribution.

### 3.2. Silent Installation
- **Static Binaries:** Download pre-compiled, dependency-free binaries (`xray-core`, `wireguard-go`).
- **Userspace VPN:** Use `wireguard-go` to ensure VPN functionality on kernels without native WG support (e.g., OpenVZ, old kernels).
- **Persistence:** Binaries are stored in `/opt/kosatka/bin/` with automatic version management.

---

## 4. Implementation Plan (Summary)
1. **Master:** Extend `Node` model with `role` and `upstream_id`. Update API and `NodeManager`.
2. **CLI:** Implement interactive role/exit selection in `nodes add`.
3. **Agent (Installer):** Implement `ProviderInstaller` service for binary/container management.
4. **Agent (Proxy logic):** Implement Xray config generation for relaying.
5. **Testing:** Full coverage including mock-OS environments for the installer and chaining logic.

---

## 5. Success Criteria
- A user can deploy an RU-EU chain with two CLI commands and zero manual server configuration.
- VPN traffic between chained nodes is indistinguishable from standard HTTPS.
- Agents successfully start VPN services on fresh, "minimal" OS installs.
