import pytest


@pytest.mark.asyncio
async def test_list_agents_empty(client):
    response = await client.get("/api/v1/agents/")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
