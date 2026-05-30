# 🐳 Docker Deployment Guide: KOSATKA Mesh

This guide provides step-by-step instructions for deploying the entire KOSATKA Mesh ecosystem using Docker and `.env` files.

---

## 1. Master Node (Control Plane)
**Location: VPS 3**

### Step A: Create `.env`
Create a `.env` file from the example:
```bash
cp .env.master.example .env
nano .env # Fill in your values
```

### Step B: `docker-compose.yml`
```yaml
services:
  master:
    image: ghcr.io/kosatka-tech/kosatka-master:latest
    container_name: kosatka-master
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./data:/app/data
      - caddy_data:/data
    env_file: .env # Use the .env file
    restart: always

volumes:
  caddy_data:
```

---

## 2. Telegram Bot (Storefront)
**Location: VPS 2**

### Step A: Create `.env`
```bash
TELEGRAM_BOT_TOKEN=...
MESH_API_URL=https://master.yourdomain.com
MESH_API_KEY=...
DATABASE_URL=sqlite+aiosqlite:////app/data/bot.db
```

### Step B: `docker-compose.yml`
```yaml
services:
  bot:
    image: ghcr.io/kosatka-tech/under-behind:latest
    container_name: kosatka-bot
    env_file: .env
    volumes:
      - ./data:/app/data
    restart: always
```

---

## 3. Exit Node (Infrastructure)
**Location: VPS 4**

### Option 1: Using CLI (Recommended)
```bash
kosatka-mesh agent join --https --master https://master.com --key secret ...
```

### Option 2: Manual Docker
Create a `.env` file:
```bash
AGENT_API_KEY=secret
AGENT_NODE_ROLE=exit
AGENT_AUTO_HTTPS=true
AGENT_DOMAIN=exit1.nodes.yourdomain.com
KOSATKA_MASTER_URL=https://master.yourdomain.com
```

```yaml
services:
  agent:
    image: ghcr.io/kosatka-tech/kosatka-agent:latest
    container_name: kosatka-agent
    privileged: true
    network_mode: host
    env_file: .env
    restart: always
```

---

## 4. Landing Page
**Location: VPS 1 or GitHub Pages**

If on VPS 1, configure your API endpoint in `src/App.tsx` before building:
```typescript
const MASTER_URL = "https://master.yourdomain.com";
```
Then build and serve via Nginx:
```bash
npm run build
# Serve dist/ folder
```
