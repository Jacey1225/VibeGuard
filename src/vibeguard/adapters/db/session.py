"""SQLAlchemy engine, session factory, and session lifecycle for a request."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def build_engine(database_url: str) -> Engine:
    """Create the SQLAlchemy engine for the configured database."""
    return create_engine(database_url)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to the given engine."""
    return sessionmaker(bind=engine, expire_on_commit=False)


def open_session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    """Yield a session for the duration of one request, then close it."""
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
