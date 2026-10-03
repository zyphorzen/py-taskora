import uuid
import pytest
from httpx2 import ASGITransport, AsyncClient

from app.core.security import decode_access_token
from app.main import app


def get_client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


@pytest.mark.asyncio
async def test_login_success_with_email():
    async with get_client() as client:
        unique_suffix = uuid.uuid4().hex[:8]
        raw_password = "Password123!"
        reg_payload = {
            "username": f"login_u_{unique_suffix}",
            "email": f"login_e_{unique_suffix}@example.com",
            "password": raw_password,
        }
        reg_res = await client.post("/auth/register", json=reg_payload)
        assert reg_res.status_code == 201
        user_id = reg_res.json()["id"]

        login_payload = {
            "email": reg_payload["email"],
            "password": raw_password,
        }
        login_res = await client.post("/auth/login", json=login_payload)
        assert login_res.status_code == 200
        token_data = login_res.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"

        payload = decode_access_token(token_data["access_token"])
        assert payload is not None
        assert payload["sub"] == user_id


@pytest.mark.asyncio
async def test_login_success_with_username():
    async with get_client() as client:
        unique_suffix = uuid.uuid4().hex[:8]
        raw_password = "Password123!"
        reg_payload = {
            "username": f"user_uname_{unique_suffix}",
            "email": f"uname_{unique_suffix}@example.com",
            "password": raw_password,
        }
        reg_res = await client.post("/auth/register", json=reg_payload)
        assert reg_res.status_code == 201

        login_payload = {
            "username": reg_payload["username"],
            "password": raw_password,
        }
        login_res = await client.post("/auth/login", json=login_payload)
        assert login_res.status_code == 200
        assert "access_token" in login_res.json()


@pytest.mark.asyncio
async def test_login_wrong_password():
    async with get_client() as client:
        unique_suffix = uuid.uuid4().hex[:8]
        reg_payload = {
            "username": f"user_wp_{unique_suffix}",
            "email": f"wp_{unique_suffix}@example.com",
            "password": "CorrectPassword123!",
        }
        await client.post("/auth/register", json=reg_payload)

        login_payload = {
            "email": reg_payload["email"],
            "password": "WrongPassword999!",
        }
        login_res = await client.post("/auth/login", json=login_payload)
        assert login_res.status_code == 401
        assert login_res.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_nonexistent_user():
    async with get_client() as client:
        login_payload = {
            "email": "ghost_nonexistent_user@example.com",
            "password": "SomePassword123!",
        }
        login_res = await client.post("/auth/login", json=login_payload)
        assert login_res.status_code == 401
        assert login_res.json()["detail"] == "Invalid email or password"
