from datetime import timedelta
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
