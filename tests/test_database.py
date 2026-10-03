import inspect
import pytest
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import Base, async_session_maker, engine, get_db


def test_base_metadata():
    assert isinstance(Base.metadata, MetaData)


def test_database_engine_config():
    assert engine.url.drivername == "postgresql+asyncpg"
    assert engine.url.database == settings.POSTGRES_DB



def test_session_maker():
    session = async_session_maker()
    assert isinstance(session, AsyncSession)
    assert session.sync_session.expire_on_commit is False


@pytest.mark.asyncio
async def test_get_db_generator():
    assert inspect.isasyncgenfunction(get_db)
    gen = get_db()
    session = await anext(gen)
    assert isinstance(session, AsyncSession)
    await gen.aclose()
