"""Pytest test fixtures and configuration."""
import os
import sys
from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure apps/api is in sys.path
api_root = Path(__file__).parent.parent
sys.path.insert(0, str(api_root))

from app.db.base import Base
from app.db.init_db import init_db
from app.core.config import settings

if not settings.SECRET_KEY:
    settings.SECRET_KEY = "test-secret-key-32-chars-long-minimum"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def test_db_session():
    """In-memory SQLite async test database session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        await init_db(session)
        yield session

    await engine.dispose()
