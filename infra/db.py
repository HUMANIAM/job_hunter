from functools import lru_cache

from sqlmodel import Session, SQLModel, create_engine

from core.config import get_settings


@lru_cache(maxsize=1)
def get_engine():
    settings = get_settings()
    return create_engine(
        settings.DATABASE_URL,
        echo=settings.SQLALCHEMY_ECHO,
    )


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(get_engine())


def get_session():
    """Yield a database session (no explicit transaction)."""
    with Session(get_engine()) as session:
        yield session
