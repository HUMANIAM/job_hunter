from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from clients.health import router as health_router
from core.config import get_settings
from core.constants import JOB_HUNTER_API_TITLE
from core.exception_handlers import register_exception_handlers


@pytest.fixture(scope="session")
def engine():
    settings = get_settings()
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture
def app():
    test_app = FastAPI(title=JOB_HUNTER_API_TITLE)
    register_exception_handlers(test_app)
    test_app.include_router(health_router)

    @test_app.get("/")
    async def root():
        return {"message": JOB_HUNTER_API_TITLE}

    return test_app


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client
