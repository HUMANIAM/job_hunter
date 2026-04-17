from __future__ import annotations

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, SQLModel, Session, create_engine

from shared.env import require_env_value

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env.postgres"

load_dotenv(ENV_FILE, override=False)


class Technology(SQLModel, table=True):
    __tablename__ = "technology"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    normalized_name: str = Field(index=True, unique=True)


DATABASE_URL = require_env_value("DATABASE_URL", error_context="PostgreSQL access")

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def get_session() -> Session:
    return SessionLocal()


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
