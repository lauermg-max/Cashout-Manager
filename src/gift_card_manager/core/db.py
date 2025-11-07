"""Database engine and session management."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .settings import settings
from ..models import account, gift_card, inventory, order, retailer, sales  # noqa: F401
from ..models.base import Base


def _build_engine(echo: bool | None = None):
    db_url = f"sqlite:///{settings.database_path.as_posix()}"
    engine = create_engine(db_url, echo=settings.debug if echo is None else echo, future=True)
    return engine


engine = _build_engine()
SessionFactory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def init_db() -> None:
    """Create database tables if they do not exist."""

    Base.metadata.create_all(engine)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around database operations."""

    session: Session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
