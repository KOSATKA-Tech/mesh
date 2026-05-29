# KOSATKA Mesh — Architecture

This document describes the moving pieces of a KOSATKA Mesh deployment
and walks through what happens during the most common operational
flows. It complements the high-level overview in
[README.md](../README.md) and the deeper provider notes under
[docs/](.).

---

## 1. Components

```
                 ┌───────────────────────────────┐
                 │            Operator           │
                 │  kosatka-mesh CLI / SDK / Bot │
                 └──────────────┬────────────────┘
                                │   X-Kosatka-Key
                                ▼
        ┌──────────────────────────────────────────────┐
        │                MASTER (FastAPI)              │
        │                                              │
        │  /api/v1/nodes/*       /api/v1/clients/*     │
        │  /api/v1/static/*      /api/v1/webhooks/*    │
        │                                              │
        │  Scheduler:                                  │
        │   • sync_all_nodes  (every SYNC_INTERVAL)    │
        │   • check_expirations (every EXPIRATION...)  │
        │                                              │
        │  Persistence: SQLAlchemy → SQLite | Postgres │
        └──────┬─────────────┬──────────────┬──────────┘
               │             │              │
   X-Kosatka-Key │      X-Kosatka-Key │  signed
               ▼             ▼              ▼
        ┌──────────┐   ┌──────────┐   ┌──────────────┐
        │ AGENT    │   │ AGENT    │   │ Webhook       │
        │ /provision│  │ /sync    │   │ subscribers   │
        │ /revoke   │  │ /capabili│   │ (e.g. bot)    │
        │ /healthz  │  │   ties   │   │               │
        └────┬─────┘   └────┬─────┘   └──────────────┘
             ▼              ▼
   ┌────────────────────────────────┐
   │ Provider (per agent process)   │
   │  • WireGuardProvider           │
   │  • AmneziaWGProvider           │
   │  • MarzbanProvider             │
   │  • XrayProvider                │
   └────────────────────────────────┘
```

### Master (`master/kosatka_master`)

* FastAPI app, single Python process per replica.
* Owns a SQL database (SQLite for dev, Postgres in production via
  `docker-compose.master.yml`).
* Apscheduler runs two background jobs (`sync_all_nodes`,
  `check_expirations`).
* Authenticates **every** `/api/v1/*` route with `X-Kosatka-Key`
  (including the `/api/v1/static/ansible.tar.gz` bootstrap tarball as
  of PR #4 — see "Node bootstrap" flow below).

### Agent (`agent/kosatka_agent`)

* FastAPI app deployed on each VPN host.
* Stateless — peer/client state lives in a JSON file on disk
  (`/opt/kosatka/agent/...`) so the master is the source of truth.
* Exposes a uniform API regardless of the underlying VPN backend
  (`provider_type=wireguard|awg|marzban|xray`). The master never
  speaks the underlying protocol; it just calls the agent.
* Authenticates inbound requests with its own `AGENT_API_KEY`
  (different from the master's `KOSATKA_API_KEY`). The master stores
  the per-agent key on the `nodes.api_key` column.

### CLI (`cli/kosatka_cli`)

* Typer-based command-line interface that wraps the master HTTP API.
* `kosatka-mesh login` writes a config file with the master URL +
  API key so subsequent commands need only the action.
* `kosatka-mesh master run` / `agent run` are *also* served by this
  package — they `uvicorn` the relevant FastAPI app in-process for
  non-Docker development.

### SDK (`sdk/KosatkaMesh`)

* Async Python client for embedding the mesh into a downstream
  service (e.g. the [under-behind](https://github.com/KOSATKA-Tech/under-behind)
  Telegram bot). Same surface as the CLI but typed and importable.

### Ansible (`ansible/`)

* Idempotent playbooks for provisioning the agent + chosen VPN
  backend on a fresh VPS.
* Served as a tarball by the master (`/api/v1/static/ansible.tar.gz`)
  and downloaded by `install.sh` on the target host.

---

## 2. Flow: bootstrapping a new agent node

```
Operator               Master                    Target VPS
   │                     │                          │
   │ kosatka-mesh deploy node …                     │
   ├────────────────────▶│                          │
   │                     │ ssh + curl install.sh ───┼──▶ install.sh
   │                     │                          │     │
   │                     │                          │     │ X-Kosatka-Key: $TOKEN
   │                     │ GET /static/ansible.tar.gz ◀───┤
   │                     │                          │     │
   │                     │ ── tar of ansible/ ─────▶│     │
   │                     │                          │     │ ansible-playbook site.yml
   │                     │                          │     ├──▶ apt install + venv + WireGuard/AWG
   │                     │                          │     │     systemd unit
   │                     │                          │     │
   │                     │                          │     │ POST /api/v1/nodes/ self-register
   │                     │ ◀────────────────────────┼─────┘
   │                     │ INSERT nodes(...)        │
   │ ◀── 200 OK ─────────┤                          │
```

1. `kosatka-mesh deploy node …` SSHes into the target VPS and runs the
   master-served `install.sh` with a one-time `--token` (the master's
   `KOSATKA_API_KEY`).
2. `install.sh` downloads the `ansible.tar.gz` tarball from the master,
   unpacks it, and runs `site.yml` against `localhost`.
3. The Ansible role brings up the agent (Docker compose-managed unit
   on systemd) and provisions the requested VPN backend.
4. The freshly-installed agent registers itself with the master via
   `POST /api/v1/nodes/` and starts answering health probes from the
   master's scheduler.

---

## 3. Flow: provisioning a VPN profile

```
Bot/CLI                Master                       Agent
   │                     │                            │
   │ POST /clients/      │                            │
   │  {name,protocol}    │                            │
   ├────────────────────▶│                            │
   │                     │ select node by capability  │
   │                     │ + load                     │
   │                     │                            │
   │                     │ POST /provision            │
   │                     │  {name, protocol}          │
   │                     ├──────── X-Kosatka-Key ────▶│
   │                     │                            │ provider.create_peer(...)
   │                     │                            │ ↓
   │                     │                            │ /etc/wireguard/wg0.conf
   │                     │                            │ + state file
   │                     │ ◀──── ProfileResponse ─────┤
   │                     │                            │
   │                     │ INSERT clients(...)        │
   │ ◀── ProfileResponse─┤                            │
```

* **Selection** — `services/node_manager.py` filters active nodes by
  the requested `protocol` (capability autodiscovery is cached on the
  `nodes` row at registration time) and picks the least-loaded one.
* **Stickiness** — once a client is created on a node, subsequent
  `GET /clients/{id}/config` calls go back to the same agent so the
  user keeps getting the same WireGuard endpoint/key pair.
* **Idempotency** — re-issuing the same `external_id` returns the
  existing client instead of creating a duplicate, so retries from the
  bot are safe.

---

## 4. Flow: scheduled node + subscription sync

The master runs two apscheduler jobs (configured via
`KOSATKA_SYNC_INTERVAL` and `KOSATKA_EXPIRATION_CHECK_INTERVAL`):

```
sync_all_nodes (every SYNC_INTERVAL seconds):
  SELECT * FROM nodes WHERE is_active
  asyncio.gather(provider.sync_node(addr) for each)
  UPDATE status, last_seen

check_expirations (every EXPIRATION_CHECK_INTERVAL seconds):
  UPDATE subscriptions SET is_active=false WHERE expires_at < now()
  → emits "subscription_expired" webhook for each
```

* Node probes are run **concurrently** (`asyncio.gather` with
  `return_exceptions=True`) so a single dead node doesn't push the
  whole tick past the next interval.
* Webhooks are signed with `KOSATKA_WEBHOOK_SECRET` and consumed by
  the bot to notify users their access was revoked.

---

## 5. Flow: webhook delivery

```
Master                                    Subscriber (bot)
  │                                          │
  │ event: subscription_expired              │
  │ payload {client_id, external_id, ...}    │
  │ X-Kosatka-Signature: hmac_sha256(...)    │
  ├─────────────────────────────────────────▶│
  │                                          │ verify signature
  │                                          │ notify Telegram user
  │ ◀── 2xx ─────────────────────────────────┤
```

`KosatkaWebhookHandler` in the SDK does the signature check; downstream
services should reject any payload that doesn't match.

---

## 6. Storage & migrations

* The schema is defined in `master/kosatka_master/models/*` via
  `DeclarativeBase`.
* On startup, `lifespan()` calls `Base.metadata.create_all` to ensure
  every defined table exists. This **does not** drop or alter columns.
* For columns added to existing tables (e.g. `nodes.api_key`),
  `_apply_lightweight_migrations()` issues idempotent
  `ALTER TABLE … ADD COLUMN` statements. Lookup is dialect-aware —
  SQLite goes through `PRAGMA table_info`, Postgres through
  `information_schema.columns WHERE table_schema='public'` so user
  schemas with same-named tables don't trick the check.
* For non-trivial schema changes Alembic is the eventual destination;
  see [#4](https://github.com/KOSATKA-Tech/mesh/pull/4) for context.

---

## 7. Authentication summary

| Scope                              | Header / Mechanism             | Source                |
| ---------------------------------- | ------------------------------ | --------------------- |
| Operator → Master `/api/v1/*`      | `X-Kosatka-Key`                | `KOSATKA_API_KEY`     |
| Operator → Master `/static/...`    | `X-Kosatka-Key`                | `KOSATKA_API_KEY`     |
| Master → Agent                     | `X-Kosatka-Key`                | `nodes.api_key` (per node) |
| Master → Webhook subscriber        | `X-Kosatka-Signature` (HMAC)   | `KOSATKA_WEBHOOK_SECRET` |

The two distinct keys (master-side vs agent-side) make per-host
rotation cheap — revoking a leaked agent key affects only that node.

---

## 8. Environment variables

| Variable                            | Component | Purpose                                |
| ----------------------------------- | --------- | -------------------------------------- |
| `KOSATKA_API_KEY`                   | master    | Inbound auth for `/api/v1/*` + `/static/*`. |
| `KOSATKA_AGENT_API_KEY`             | master    | Master→agent auth (defaults to `KOSATKA_API_KEY`). |
| `KOSATKA_DATABASE_URL`              | master    | SQLAlchemy async URL.                  |
| `KOSATKA_WEBHOOK_SECRET`            | master    | HMAC signing key for outgoing webhooks. |
| `KOSATKA_SYNC_INTERVAL`             | master    | Seconds between node-health probes.    |
| `KOSATKA_EXPIRATION_CHECK_INTERVAL` | master    | Seconds between subscription sweeps.   |
| `AGENT_API_KEY`                     | agent     | Inbound auth for the agent's API.      |
| `AGENT_PROVIDER_TYPE`               | agent     | `wireguard` / `awg` / `marzban` / `xray`. |
| `AGENT_MARZBAN_*`                   | agent     | Marzban-specific provider creds.       |
| `KOSATKA_MASTER_URL`                | scripts   | Used by `install.sh` / register flows. |

See [`.env.master.example`](../.env.master.example) and
[`.env.agent.example`](../.env.agent.example) for the canonical
templates.

---

## 9. Performance notes

* `sync_all_nodes` probes agents **in parallel** — see PR #5.
* Master's HTTP client to agents is `httpx.AsyncClient` (connection
  pooling + HTTP/2) created per request; if you grow past ~50 active
  nodes, switch to a long-lived `AsyncClient` to amortise TLS handshakes.
* `_resolve_ansible_dir()` walks the filesystem once per request to
  the bootstrap endpoint. The tarball is rebuilt each time — fine at
  bootstrap-frequency, but cache to `/tmp/ansible.tar.gz` if you ever
  surface it on a hot path.
