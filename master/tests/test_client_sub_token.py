import uuid

import pytest
from kosatka_master.models.client import Client
from sqlalchemy import select


@pytest.mark.asyncio
async def test_client_subscription_fields(db_session):
    # 1. Create a new client
    new_client = Client(external_id="test-external-id")
    db_session.add(new_client)
    await db_session.commit()
    await db_session.refresh(new_client)

    # 2. Verify sub_token is automatically generated and is a valid UUID
    # This should fail because sub_token doesn't exist yet
    assert hasattr(new_client, "sub_token")
    assert new_client.sub_token is not None
    assert isinstance(new_client.sub_token, str)
    # Check if it's a valid UUID
    uuid.UUID(new_client.sub_token)

    # 3. Verify sub_enabled is True by default
    assert hasattr(new_client, "sub_enabled")
    assert new_client.sub_enabled is True

    # 4. Verify lookup by sub_token
    stmt = select(Client).where(Client.sub_token == new_client.sub_token)
    result = await db_session.execute(stmt)
    found_client = result.scalar_one()
    assert found_client.id == new_client.id
