from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, SQLModel, Session, create_engine

from core.config import get_settings


class Technology(SQLModel, table=True):
    __tablename__ = "technology"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    normalized_name: str = Field(index=True, unique=True)


settings = get_settings()
DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL, echo=settings.SQLALCHEMY_ECHO, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def get_session() -> Session:
    return SessionLocal()


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
