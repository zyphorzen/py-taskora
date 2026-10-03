import uuid
import pytest
from httpx2 import ASGITransport, AsyncClient

from app.main import app


def get_client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


@pytest.mark.asyncio
async def test_register_success():
    async with get_client() as client:
        unique_suffix = uuid.uuid4().hex[:8]
        payload = {
            "username": f"user_{unique_suffix}",
            "email": f"user_{unique_suffix}@example.com",
            "password": "strongPassword123!",
        }
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == payload["username"]
        assert data["email"] == payload["email"]
        assert "password" not in data
        assert "hashed_password" not in data
        assert "id" in data
        assert data["is_active"] is True


@pytest.mark.asyncio
async def test_register_duplicate_email():
    async with get_client() as client:
        unique_suffix = uuid.uuid4().hex[:8]
        payload = {
            "username": f"user_{unique_suffix}",
            "email": f"duplicate_{unique_suffix}@example.com",
            "password": "strongPassword123!",
        }
        res1 = await client.post("/auth/register", json=payload)
        assert res1.status_code == 201

        payload_duplicate_email = {
            "username": f"another_{unique_suffix}",
            "email": payload["email"],
            "password": "strongPassword123!",
        }
        res2 = await client.post("/auth/register", json=payload_duplicate_email)
        assert res2.status_code == 409
        assert res2.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_register_duplicate_username():
    async with get_client() as client:
        unique_suffix = uuid.uuid4().hex[:8]
        payload = {
            "username": f"dupuser_{unique_suffix}",
            "email": f"user1_{unique_suffix}@example.com",
            "password": "strongPassword123!",
        }
        res1 = await client.post("/auth/register", json=payload)
        assert res1.status_code == 201

        payload_duplicate_username = {
            "username": payload["username"],
            "email": f"user2_{unique_suffix}@example.com",
            "password": "strongPassword123!",
        }
        res2 = await client.post("/auth/register", json=payload_duplicate_username)
        assert res2.status_code == 409
        assert res2.json()["detail"] == "Username already taken"


@pytest.mark.asyncio
async def test_register_validation_error():
    async with get_client() as client:

        payload_short_password = {
            "username": "validuser",
            "email": "valid@example.com",
            "password": "123",
        }
        response = await client.post("/auth/register", json=payload_short_password)
        assert response.status_code == 422

        payload_bad_email = {
            "username": "validuser",
            "email": "not-an-email",
            "password": "validPassword123!",
        }
        response = await client.post("/auth/register", json=payload_bad_email)
        assert response.status_code == 422
