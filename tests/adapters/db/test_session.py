"""Tests for SQLAlchemy engine/session construction and lifecycle."""

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from vibeguard.adapters.db.session import build_engine, build_session_factory, open_session


def test_build_engine_connects_to_the_given_database(db_engine: Engine):
    engine = build_engine(str(db_engine.url))
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar() == 1
    finally:
        engine.dispose()


def test_open_session_yields_a_working_session_and_closes_it(db_engine: Engine):
    session_factory = build_session_factory(db_engine)
    generator = open_session(session_factory)
    session = next(generator)

    assert session.execute(text("SELECT 1")).scalar() == 1

    with pytest.raises(StopIteration):
        next(generator)
