import uuid
from datetime import timedelta
import pytest
from httpx2 import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.main import app


def get_client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    )


@pytest.mark.asyncio
async def test_get_current_user_success():
    async with get_client() as client:
        unique_suffix = uuid.uuid4().hex[:8]
        reg_payload = {
            "username": f"me_user_{unique_suffix}",
            "email": f"me_{unique_suffix}@example.com",
            "password": "Password123!",
        }
        reg_res = await client.post("/auth/register", json=reg_payload)
        assert reg_res.status_code == 201

        login_res = await client.post(
            "/auth/login",
            json={
                "email": reg_payload["email"],
                "password": reg_payload["password"],
            },
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}
        me_res = await client.get("/auth/me", headers=headers)
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["username"] == reg_payload["username"]
        assert me_data["email"] == reg_payload["email"]
        assert me_data["is_active"] is True
        assert "password" not in me_data
        assert "hashed_password" not in me_data


@pytest.mark.asyncio
async def test_get_current_user_unauthorized_missing_token():
    async with get_client() as client:
        res = await client.get("/auth/me")
        assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    async with get_client() as client:
        headers = {"Authorization": "Bearer invalid.token.value"}
        res = await client.get("/auth/me", headers=headers)
        assert res.status_code == 401
        assert res.json()["detail"] == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_expired_token():
    async with get_client() as client:
        fake_user_id = str(uuid.uuid4())
        expired_token = create_access_token(
            subject=fake_user_id,
            expires_delta=timedelta(minutes=-5),
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        res = await client.get("/auth/me", headers=headers)
        assert res.status_code == 401
        assert res.json()["detail"] == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_nonexistent_user_id():
    async with get_client() as client:
        random_user_id = str(uuid.uuid4())
        token = create_access_token(subject=random_user_id)
        headers = {"Authorization": f"Bearer {token}"}
        res = await client.get("/auth/me", headers=headers)
        assert res.status_code == 401
        assert res.json()["detail"] == "User not found"
