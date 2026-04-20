import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.constants import JOB_HUNTER_API_TITLE as APP_TITLE
from core.exception_handlers import register_exception_handlers
from core.logging import setup_logging
from infra.db import create_db_and_tables
from clients.candidate_profiling.candidate_route import router as candidate_router
from clients.health import router as health_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    create_db_and_tables()
    yield


app = FastAPI(title=APP_TITLE, lifespan=lifespan)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_BASE_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(candidate_router)

@app.get("/")
async def root():
    return {"message": APP_TITLE}
