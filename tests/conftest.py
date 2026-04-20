from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, List

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from clients.candidate_profiling.candidate_profiling_model import CandidateProfileRecord
from clients.candidate_profiling.candidate_route import router as candidate_router
from infra.db import get_session
from tests.data.candidate import make_candidate_profile_endpoint_record

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from clients.health import router as health_router
from core.config import get_settings
from core.constants import JOB_HUNTER_API_TITLE
from core.exception_handlers import register_exception_handlers

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
