"""``/api/v1/static/ansible.tar.gz`` was previously unauthenticated.

The endpoint serves the entire ansible/ tree, which contains the agent
self-bootstrap playbooks \u2014 anyone who could reach the master could
download a recipe for joining the mesh. PR #4 put it behind the same
``X-Kosatka-Key`` header as the rest of ``/api/v1/*``; these tests
prevent a regression.
"""

import pytest
from kosatka_master.config import settings


@pytest.mark.asyncio
async def test_ansible_tarball_requires_api_key(client):
    response = await client.get("/api/v1/static/ansible.tar.gz")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ansible_tarball_rejects_wrong_api_key(client):
    response = await client.get(
        "/api/v1/static/ansible.tar.gz",
        headers={"X-Kosatka-Key": "definitely-not-the-real-key"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_ansible_tarball_accepts_valid_api_key(client):
    response = await client.get(
        "/api/v1/static/ansible.tar.gz",
        headers={"X-Kosatka-Key": settings.api_key},
    )
    # Test fixture's dev cwd has an ``ansible/`` directory at the repo root,
    # so the resolver succeeds and we get a 200 with the gzipped tar.
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/")
