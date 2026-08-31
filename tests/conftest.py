import asyncio
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.storage.dependencies import get_storage_provider
from app.storage.local import LocalStorageProvider


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    asyncio.run(_create_schema(engine))

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    storage = LocalStorageProvider(tmp_path / "uploads")

    def override_get_storage_provider() -> LocalStorageProvider:
        return storage

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_storage_provider] = override_get_storage_provider

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


async def _create_schema(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def register_user(client: TestClient):
    def _register(
        email: str = "test@example.com", password: str = "password123"
    ) -> dict:
        response = client.post(
            "/api/v1/auth/register", json={"email": email, "password": password}
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _register


@pytest.fixture
def auth_headers(client: TestClient, register_user) -> dict[str, str]:
    email = "test@example.com"
    password = "password123"
    register_user(email=email, password=password)

    response = client.post(
        "/api/v1/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
