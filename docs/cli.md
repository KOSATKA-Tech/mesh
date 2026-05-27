# KOSATKA CLI

The `kosatka-mesh` CLI is the primary tool for managing your global VPN mesh.

## Installation

From the root of the monorepo:
```bash
uv pip install -e .
```

## Global Commands

- `kosatka-mesh login [URL] [API_KEY]`: Authenticate with a Master instance.
- `kosatka-mesh info`: Show current CLI configuration.
- `kosatka-mesh doctor`: Run diagnostic checks.

## Service Management

- `kosatka-mesh master run`: Start the Kosatka Master service.
- `kosatka-mesh agent run`: Start the Kosatka Agent service.

## Node Management

- `kosatka-mesh nodes list`: List all registered nodes.
- `kosatka-mesh nodes add NAME ADDRESS`: Register a new node.
- `kosatka-mesh nodes remove`: Remove a node.

## Infrastructure & Security

- `kosatka-mesh host status`: Show real-time host metrics (CPU, RAM, Disk, Temp) for all nodes.
- `kosatka-mesh host clean [--node-id ID]`: Trigger manual host cleanup (Docker prune, logs) on all or specific nodes.
- `kosatka-mesh dns-setup --provider PROV --base-domain DOMAIN`: Configure automated DNS/SSL (currently supports `beget`, `manual`).

## Deployment
...
- `kosatka-mesh deploy`: Run Ansible playbooks for infrastructure setup.
