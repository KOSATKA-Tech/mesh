from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class NodeBase(BaseModel):
    name: str
    address: str
    provider_type: str = "agent"


class NodeCreate(NodeBase):
    api_key: Optional[str] = None


class Node(NodeBase):
    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: int
    status: str = "offline"
    is_active: bool = True


class ClientBase(BaseModel):
    external_id: str
    email: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class Client(ClientBase):
    """SDK-side client record.

    `config_text`, `address`, `public_key`, `node_id`, `provider_type`
    are populated by `provision()` but absent from the plain `/clients`
    CRUD responses; they are optional here so both code paths parse.
    """

    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: int
    is_active: bool = True
    created_at: Optional[datetime] = None

    # Provisioning extras — present after a provision() call.
    config_text: Optional[str] = None
    address: Optional[str] = None
    public_key: Optional[str] = None
    node_id: Optional[int] = None
    provider_type: Optional[str] = None
    sub_token: Optional[str] = None


class ProvisionRequest(BaseModel):
    external_id: str
    email: Optional[str] = None
    protocol: str = "awg"
    node_id: Optional[int] = None


class SubscriptionBase(BaseModel):
    client_id: int
    plan_name: str
    expires_at: datetime


class SubscriptionCreate(SubscriptionBase):
    pass


class Subscription(SubscriptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool


class WebhookEvent(BaseModel):
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime
