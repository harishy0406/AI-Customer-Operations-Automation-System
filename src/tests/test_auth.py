import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.models.tenant import Tenant
from src.api.services.auth_service import create_user


@pytest.mark.asyncio
async def test_login_flow(client: AsyncClient, db_session: AsyncSession):
    tenant = Tenant(id="t1", name="Test Tenant", plan="free")
    db_session.add(tenant)
    await db_session.flush()

    await create_user(db_session, tenant_id="t1", email="admin@test.com", password="testpass123", role="admin")
    await db_session.commit()

    response = await client.post("/auth/login", json={
        "email": "admin@test.com",
        "password": "testpass123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    response = await client.post("/auth/login", json={
        "email": "nonexistent@test.com",
        "password": "wrong",
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_health_no_auth(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_protected_endpoint_no_token(client: AsyncClient):
    response = await client.post("/v1/query", json={"query": "hello"})
    assert response.status_code == 401
