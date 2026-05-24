# Design Spec: Universal Experience & Subscriptions (Phase 4)

**Date:** 2026-05-24
**Status:** Approved
**Goal:** Provide a seamless "set it and forget it" experience for end-users via universal Clash-compatible subscriptions and unified sing-box transport.

---

## 1. Unified Transport (Sing-box as Primary)
Consolidate all VPN protocols under the **sing-box** core for better performance and maintainability.

### 1.1. Core Consolidation
- Use `sing-box` for everything: WireGuard, Hysteria2, TUIC, and VLESS/Reality.
- Existing providers (Xray, WireGuard-go) will remain for legacy but `sing-box` will be the default for new deployments.

---

## 2. Subscription Management (Master)
Transform the Master node into a subscription provider that delivers dynamic configurations to clients.

### 2.1. Subscription Tokens
- Add a `sub_token` field to the `Client` model (UUID).
- Endpoint: `GET /sub/{token}`.
- Logic:
    - Resolves the client by token.
    - Aggregates all available and healthy nodes/chains for the client.
    - Returns a **Clash-compatible YAML** or a **Sing-box JSON** configuration.

### 2.2. Clash YAML Generator
- **Proxies:** List of all available endpoints (concealing intermediary relays).
- **Proxy Groups:**
    - `🚀 Auto Select`: Automatically picks the lowest latency node.
    - `🛠 Manual Select`: User picks a specific country.
- **Rules:**
    - Bypass local/private IPs.
    - Route everything else through Kosatka Mesh.

---

## 3. Intelligent Node Naming
- Use GeoIP data to automatically label nodes in the subscription file (e.g., `🇳🇱 Netherlands [Premium]`).
- Conceal internal topology (Relay IDs) from the end-user.

---

## 4. Implementation Steps
1.  **Master:** Update `Client` model with `sub_token`. Add migration.
2.  **Master:** Implement `SubscriptionGenerator` to produce Clash YAML.
3.  **Master:** Add `GET /sub/{token}` endpoint with appropriate headers for auto-updating.
4.  **Agent:** Refactor `sing-box` providers to ensure they support all client connection types needed for the subscription.
5.  **SDK/CLI:** Add commands to retrieve or refresh a client's subscription link.

---

## 5. Testing Plan
- **Subscription API Tests:** Verify that the token-based lookup works and returns 200 OK with valid YAML.
- **YAML Validation:** Use a YAML parser to ensure the generated config is syntactically correct for Clash.
- **Privacy Tests:** Ensure relay node IPs are NOT exposed in the final `proxies` list (only Entry node addresses).
- **Multi-Hop Config Tests:** Verify that a multi-hop chain is correctly represented as a single logical proxy in the client config.
