from __future__ import annotations

from pathlib import Path
from typing import List
from uuid import uuid4

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from pytest_postgresql import factories
from sqlmodel import Session, SQLModel, create_engine

from clients.candidate_profiling.candidate_route import router as candidate_router
from infra.db import get_session

from clients.health import router as health_router
from core.config import get_settings
from core.constants import JOB_HUNTER_API_TITLE
from core.exception_handlers import register_exception_handlers

settings = get_settings()
database_url = make_url(settings.DATABASE_URL)
if database_url.get_backend_name() != "postgresql":
    raise RuntimeError("Integration tests require a PostgreSQL DATABASE_URL")

postgresql_noproc = factories.postgresql_noproc(
    host=database_url.host,
    port=database_url.port,
    user=database_url.username,
    password=database_url.password,
    dbname=f"{database_url.database}_pytest_{uuid4().hex}",
)
postgresql = factories.postgresql("postgresql_noproc")


def create_mock_app(session: Session, routers: List[APIRouter]) -> FastAPI:
    """
    Helper function to create a FastAPI app with specified routers.

    Args:
        session: Database session to be used in dependency overrides
        routers: List of APIRouter instances to include in the app

    Returns:
        FastAPI app instance with routers included
    """
    test_app = FastAPI(title=JOB_HUNTER_API_TITLE)
    test_app.dependency_overrides[get_session] = lambda: session

    register_exception_handlers(test_app)
    for router in routers:
        test_app.include_router(router)

    @test_app.get("/")
    async def root():
        return {"message": JOB_HUNTER_API_TITLE}

    return test_app


@pytest.fixture
def engine(postgresql):
    test_engine = create_engine(
        database_url.set(
            drivername="postgresql+psycopg",
            database=postgresql.info.dbname,
            username=postgresql.info.user,
            password=postgresql.info.password,
            host=postgresql.info.host,
            port=postgresql.info.port,
        ),
        echo=False,
    )
    SQLModel.metadata.create_all(test_engine)
    try:
        yield test_engine
    finally:
        SQLModel.metadata.drop_all(test_engine)
        test_engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def app(session):
    routers = [
        health_router,
        candidate_router,
    ]

    app = create_mock_app(session, routers)
    app.session = session
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        client.session = app.session
        yield client
