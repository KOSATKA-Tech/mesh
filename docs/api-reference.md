# API Reference

The KOSATKA Master provides a RESTful API for managing the mesh.

## Authentication
All requests must include the `X-Kosatka-Key` header.

## Endpoints

### Nodes
- `GET /api/v1/nodes`: List all nodes.
- `POST /api/v1/nodes`: Register a new node.
- `GET /api/v1/nodes/{id}`: Get node details.

### Subscriptions
- `GET /api/v1/subscriptions`: List all subscriptions.
- `POST /api/v1/subscriptions`: Create a new subscription.

### Events
- `GET /api/v1/events`: List recent events.
