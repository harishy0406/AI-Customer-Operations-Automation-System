import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "AI Customer Operations" in data["service"]


@pytest.mark.asyncio
async def test_liveness_endpoint(client: AsyncClient):
    response = await client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness_endpoint_success(client: AsyncClient, monkeypatch):
    async def fake_db_ok():
        return True

    async def fake_redis_ok(_):
        return True

    monkeypatch.setattr("src.api.main.check_database", fake_db_ok)
    monkeypatch.setattr("src.api.main.check_redis", fake_redis_ok)

    response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["redis"] == "ok"


@pytest.mark.asyncio
async def test_readiness_endpoint_failure(client: AsyncClient, monkeypatch):
    async def fake_db_fail():
        return False

    async def fake_redis_ok(_):
        return True

    monkeypatch.setattr("src.api.main.check_database", fake_db_fail)
    monkeypatch.setattr("src.api.main.check_redis", fake_redis_ok)

    response = await client.get("/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["database"] == "failed"
    assert data["checks"]["redis"] == "ok"
