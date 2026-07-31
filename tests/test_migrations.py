"""Validates the Alembic migration itself, not just Base.metadata.create_all()."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrade_head_creates_expected_schema(
    postgresql_conn, monkeypatch: pytest.MonkeyPatch
):
    info = postgresql_conn.info
    database_url = f"postgresql+psycopg://{info.user}@{info.host}:{info.port}/{info.dbname}"
    monkeypatch.setenv("VIBEGUARD_DATABASE_URL", database_url)

    repo_root = Path(__file__).resolve().parent.parent
    config = Config(str(repo_root / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "migrations"))

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {"repositories", "repository_files"} <= tables

        repo_file_fks = inspector.get_foreign_keys("repository_files")
        assert any(fk["referred_table"] == "repositories" for fk in repo_file_fks)
    finally:
        engine.dispose()

    command.downgrade(config, "base")
