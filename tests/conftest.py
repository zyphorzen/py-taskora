import uuid
from typing import AsyncGenerator
import pytest_asyncio
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.user import User


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client fixture."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Database async session fixture."""
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def create_user(db_session: AsyncSession):
    """Factory fixture to create test users."""

    async def _create(
        username: str | None = None,
        email: str | None = None,
        password: str = "SecurePass123!",
        is_active: bool = True,
    ) -> User:
        suffix = uuid.uuid4().hex[:8]
        user = User(
            username=username or f"user_{suffix}",
            email=email or f"user_{suffix}@example.com",
            hashed_password=get_password_hash(password),
            is_active=is_active,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _create


@pytest_asyncio.fixture
async def active_user(create_user) -> User:
    """Fixture providing a standard active user."""
    return await create_user(is_active=True)


@pytest_asyncio.fixture
async def inactive_user(create_user) -> User:
    """Fixture providing an inactive user."""
    return await create_user(is_active=False)


@pytest_asyncio.fixture
async def user_and_token(active_user: User):
    """Fixture providing an active user, token, and auth headers."""
    token = create_access_token(subject=str(active_user.id))
    headers = {"Authorization": f"Bearer {token}"}
    return active_user, token, headers


@pytest_asyncio.fixture
async def auth_headers(user_and_token) -> dict[str, str]:
    """Fixture providing Authorization headers for an authenticated user."""
    _, _, headers = user_and_token
    return headers
