import uuid
from datetime import timedelta
import pytest
from httpx2 import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User


class TestAuthRegistration:
    """Comprehensive tests for user registration."""

    async def test_register_success(self, client: AsyncClient):
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "username": f"reg_{suffix}",
            "email": f"reg_{suffix}@example.com",
            "password": "StrongPassword123!",
        }
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == payload["username"]
        assert data["email"] == payload["email"]
        assert data["is_active"] is True
        assert "password" not in data
        assert "hashed_password" not in data
        assert uuid.UUID(data["id"])

    async def test_register_duplicate_email(
        self, client: AsyncClient, active_user: User
    ):
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "username": f"diff_user_{suffix}",
            "email": active_user.email,
            "password": "StrongPassword123!",
        }
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 409
        assert response.json()["detail"] == "Email already registered"

    async def test_register_duplicate_username(
        self, client: AsyncClient, active_user: User
    ):
        suffix = uuid.uuid4().hex[:8]
        payload = {
            "username": active_user.username,
            "email": f"diff_{suffix}@example.com",
            "password": "StrongPassword123!",
        }
        response = await client.post("/auth/register", json=payload)
        assert response.status_code == 409
        assert response.json()["detail"] == "Username already taken"

    @pytest.mark.parametrize(
        "invalid_payload",
        [
            {"username": "usr", "email": "bad-email", "password": "Pass123456!"},
            {"username": "usr", "email": "usr@example.com", "password": "short"},
            {"username": "", "email": "usr@example.com", "password": "Pass123456!"},
            {"email": "usr@example.com", "password": "Pass123456!"},
            {"username": "usr", "password": "Pass123456!"},
        ],
    )
    async def test_register_validation_errors(
        self, client: AsyncClient, invalid_payload: dict
    ):
        response = await client.post("/auth/register", json=invalid_payload)
        assert response.status_code == 422


class TestAuthLogin:
    """Comprehensive tests for user login and token issuance."""

    async def test_login_with_email_success(self, client: AsyncClient, create_user):
        raw_password = "SecretPassword123!"
        user = await create_user(password=raw_password)
        payload = {"email": user.email, "password": raw_password}

        response = await client.post("/auth/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        claims = decode_access_token(data["access_token"])
        assert claims is not None
        assert claims["sub"] == str(user.id)

    async def test_login_with_username_success(self, client: AsyncClient, create_user):
        raw_password = "SecretPassword123!"
        user = await create_user(password=raw_password)
        payload = {"username": user.username, "password": raw_password}

        response = await client.post("/auth/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, active_user: User):
        payload = {"email": active_user.email, "password": "IncorrectPassword999!"}
        response = await client.post("/auth/login", json=payload)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    async def test_login_nonexistent_user(self, client: AsyncClient):
        payload = {"email": "nonexistent_ghost@example.com", "password": "Password123!"}
        response = await client.post("/auth/login", json=payload)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"

    async def test_login_inactive_user(self, client: AsyncClient, inactive_user: User):
        payload = {"email": inactive_user.email, "password": "SecurePass123!"}
        response = await client.post("/auth/login", json=payload)
        assert response.status_code == 400
        assert response.json()["detail"] == "Inactive user account"

    async def test_login_missing_identifier(self, client: AsyncClient):
        payload = {"password": "Password123!"}
        response = await client.post("/auth/login", json=payload)
        assert response.status_code == 422


class TestAuthProtectedEndpoints:
    """Comprehensive tests for JWT verification and protected routes."""

    async def test_get_current_user_me_success(
        self, client: AsyncClient, user_and_token
    ):
        user, _, headers = user_and_token
        response = await client.get("/auth/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user.id)
        assert data["username"] == user.username
        assert data["email"] == user.email
        assert data["is_active"] is True
        assert "hashed_password" not in data

    async def test_get_current_user_no_auth_header(self, client: AsyncClient):
        response = await client.get("/auth/me")
        assert response.status_code in (401, 403)

    async def test_get_current_user_invalid_token(self, client: AsyncClient):
        headers = {"Authorization": "Bearer not.a.valid.jwt.token"}
        response = await client.get("/auth/me", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"

    async def test_get_current_user_expired_token(
        self, client: AsyncClient, active_user: User
    ):
        expired_token = create_access_token(
            subject=str(active_user.id),
            expires_delta=timedelta(minutes=-10),
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = await client.get("/auth/me", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"

    async def test_get_current_user_non_uuid_subject(self, client: AsyncClient):
        tampered_token = create_access_token(subject="not-a-valid-uuid")
        headers = {"Authorization": f"Bearer {tampered_token}"}
        response = await client.get("/auth/me", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Could not validate credentials"

    async def test_get_current_user_nonexistent_user_id(self, client: AsyncClient):
        random_id = str(uuid.uuid4())
        token = create_access_token(subject=random_id)
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/auth/me", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "User not found"

    async def test_get_current_user_inactive_user(
        self, client: AsyncClient, inactive_user: User
    ):
        token = create_access_token(subject=str(inactive_user.id))
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/auth/me", headers=headers)
        assert response.status_code == 400
        assert response.json()["detail"] == "Inactive user account"


class TestSecurityUtilities:
    """Unit tests for password and JWT utility functions."""

    def test_password_hashing_and_verification(self):
        plain_password = "SuperSecretPassword123!"
        hashed = get_password_hash(plain_password)
        assert hashed.startswith("$argon2id$")
        assert verify_password(plain_password, hashed) is True
        assert verify_password("WrongPassword123!", hashed) is False

    def test_jwt_token_creation_and_expiration(self):
        subject = "test-subject"
        token = create_access_token(
            subject=subject, expires_delta=timedelta(minutes=15)
        )
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == subject
        assert "exp" in payload

    def test_decode_invalid_token(self):
        assert decode_access_token("gibberish-token") is None
