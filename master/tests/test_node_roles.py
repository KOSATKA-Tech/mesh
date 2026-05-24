import pytest
from kosatka_master.models.node import Node
from sqlalchemy import select


@pytest.mark.asyncio
async def test_node_roles_and_upstream(db_session):
    # Create an exit node
    exit_node = Node(name="exit-node", address="1.1.1.1", provider_type="agent", role="exit")
    db_session.add(exit_node)
    await db_session.commit()
    await db_session.refresh(exit_node)

    # Create a proxy node pointing to the exit node
    proxy_node = Node(
        name="proxy-node",
        address="2.2.2.2",
        provider_type="agent",
        role="proxy",
        upstream_id=exit_node.id,
    )
    db_session.add(proxy_node)
    await db_session.commit()
    await db_session.refresh(proxy_node)

    # Verify retrieval
    stmt = select(Node).where(Node.name == "proxy-node")
    result = await db_session.execute(stmt)
    retrieved_proxy = result.scalar_one()

    assert retrieved_proxy.role == "proxy"
    assert retrieved_proxy.upstream_id == exit_node.id
