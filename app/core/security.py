from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

pwd_hasher = PasswordHasher()


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return pwd_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2 hash."""
    try:
        return pwd_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False
