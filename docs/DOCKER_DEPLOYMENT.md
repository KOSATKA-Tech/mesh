# 🐳 Docker Deployment Guide: KOSATKA Mesh

This guide provides step-by-step instructions for deploying the entire KOSATKA Mesh ecosystem using Docker and Docker Compose. This approach is ideal for rapid scaling and easy maintenance.

---

## 🏗 System Components

1.  **Master Node**: The central control plane (API + Admin UI).
2.  **Exit Node**: A server that terminates VPN traffic to the open internet.
3.  **Relay Node (Optional)**: An intermediate server for traffic chaining (Multi-Hop) to increase privacy and bypass censorship.

---

## 1. Master Node Deployment

The Master node orchestrates the entire mesh. It requires a public IP and a domain for SSL.

### `docker-compose.yml` (Master)
```yaml
services:
  master:
    image: ghcr.io/kosatka-tech/kosatka-master:latest
    container_name: kosatka-master
    ports:
      - "80:80"   # HTTP-01 challenge for Let's Encrypt
      - "443:443" # Secure Admin UI and API
    volumes:
      - ./data:/app/data
      - caddy_data:/data
      - caddy_config:/config
    environment:
      - KOSATKA_API_KEY=your-secure-api-key
      - KOSATKA_DOMAIN=master.yourdomain.com
      - KOSATKA_AUTO_HTTPS=true
      - DATABASE_URL=sqlite+aiosqlite:////app/data/kosatka.db
    restart: always

volumes:
  caddy_data:
  caddy_config:
```

### Steps:
1.  Point `master.yourdomain.com` to your VPS IP.
2.  Run `docker compose up -d`.
3.  Access UI at `https://master.yourdomain.com/admin/`.

---

## 2. Exit Node Deployment (Standalone)

An Exit node provides users with a direct connection to the internet from its IP.

### `docker-compose.yml` (Exit Node)
```yaml
services:
  agent:
    image: ghcr.io/kosatka-tech/kosatka-agent:latest
    container_name: kosatka-agent
    privileged: true # Required for WireGuard/Amnezia kernel modules
    network_mode: host # Simplifies UDP port management
    environment:
      - AGENT_API_KEY=your-secure-api-key # Must match Master
      - AGENT_NODE_ROLE=exit
      - AGENT_AUTO_HTTPS=true
      - AGENT_DOMAIN=exit1.nodes.yourdomain.com
      - KOSATKA_MASTER_URL=https://master.yourdomain.com
    restart: always
```

---

## 3. Advanced Scenario: Traffic Chaining (Relay + Exit)

In this setup, traffic flows: `User -> Relay (Intermediate) -> Exit (Target) -> Internet`.

### Step A: Deploy the Relay Node
Relay nodes act as entry points but don't exit to the internet themselves.

```yaml
services:
  relay:
    image: ghcr.io/kosatka-tech/kosatka-agent:latest
    container_name: kosatka-relay
    privileged: true
    network_mode: host
    environment:
      - AGENT_API_KEY=your-secure-api-key
      - AGENT_NODE_ROLE=proxy # 'proxy' role for intermediate hops
      - AGENT_AUTO_HTTPS=true
      - AGENT_DOMAIN=relay.nodes.yourdomain.com
      - KOSATKA_MASTER_URL=https://master.yourdomain.com
```

### Step B: Deploy the Exit Node
Same as Step 2, but ensure it's registered with a different name in the Master.

### Step C: Chain them in Admin UI
1.  Open the **Network Map** in your Admin Panel.
2.  Locate your **Relay** node and your **Exit** node.
3.  Click and drag a line from the **Relay** to the **Exit**.
4.  KOSATKA will automatically provision an Xray/Reality tunnel between them.

---

## 🛡 Security Hardening (Host Level)

While Docker isolates the processes, we recommend running these commands on your host VPS:

```bash
# Install UFW
sudo apt update && sudo apt install ufw -y

# Allow essential ports
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw allow 51820/udp # WireGuard (Default)

# Enable firewall
sudo ufw enable
```

---

## 🔑 Environment Variables Reference

| Variable | Description |
| :--- | :--- |
| `KOSATKA_API_KEY` | Secret token for Master-Agent communication. |
| `KOSATKA_DOMAIN` | Public domain for the Master node UI/API. |
| `KOSATKA_AUTO_HTTPS` | Set to `true` to enable automatic SSL via Caddy. |
| `AGENT_NODE_ROLE` | `exit` (Direct access) or `proxy` (Intermediate hop). |
| `AGENT_DOMAIN` | Unique domain for the Agent (e.g. `nl.nodes.com`). |
