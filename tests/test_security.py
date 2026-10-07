from datetime import timedelta
import jwt
from httpx2 import AsyncClient

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hashing():
    raw_password = "SecretPassword123!"
    hashed = get_password_hash(raw_password)

    assert hashed != raw_password
    assert hashed.startswith("$argon2id$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_flow():
    token = create_access_token(subject="user-uuid-123")
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "user-uuid-123"
    assert "exp" in decoded


def test_jwt_invalid_token():
    assert decode_access_token("invalid.token.signature") is None


def test_expired_jwt_token():
    token = create_access_token(
        subject="user-uuid-123",
        expires_delta=timedelta(minutes=-1),
    )
    decoded = decode_access_token(token)
    assert decoded is None


def test_jwt_tampered_signature():
    token = create_access_token(subject="user-uuid-123")
    tampered = token[:-4] + "abcd"
    assert decode_access_token(tampered) is None


def test_jwt_wrong_secret():
    token = jwt.encode(
        {"sub": "user-uuid-123"},
        "wrong-secret-key-12345678901234567890",
        algorithm=settings.ALGORITHM,
    )
    assert decode_access_token(token) is None


def test_jwt_algorithm_mismatch():
    token = jwt.encode(
        {"sub": "user-uuid-123"},
        settings.SECRET_KEY,
        algorithm="HS384",
    )
    assert decode_access_token(token) is None


async def test_security_headers_present(client: AsyncClient):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("x-xss-protection") == "1; mode=block"
    assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
