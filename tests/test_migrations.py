"""Validates the Alembic migration itself, not just Base.metadata.create_all()."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from tests.adapters.config.test_settings import _REQUIRED_ENV


def test_alembic_upgrade_head_creates_expected_schema(
    postgresql_conn, monkeypatch: pytest.MonkeyPatch
):
    info = postgresql_conn.info
    database_url = f"postgresql+psycopg://{info.user}@{info.host}:{info.port}/{info.dbname}"
    for key, value in _REQUIRED_ENV.items():
        monkeypatch.setenv(key, str(value))
    monkeypatch.setenv("VIBEGUARD_DATABASE_URL", database_url)

    repo_root = Path(__file__).resolve().parent.parent
    config = Config(str(repo_root / "alembic.ini"))
    config.set_main_option("script_location", str(repo_root / "migrations"))

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {
            "repositories",
            "repository_files",
            "findings",
            "users",
            "sessions",
            "remediations",
            "remediation_findings",
        } <= tables

        repo_file_fks = inspector.get_foreign_keys("repository_files")
        assert any(fk["referred_table"] == "repositories" for fk in repo_file_fks)

        finding_fks = inspector.get_foreign_keys("findings")
        assert any(fk["referred_table"] == "repositories" for fk in finding_fks)

        repositories_columns = {col["name"] for col in inspector.get_columns("repositories")}
        assert {"scan_incomplete", "scan_incomplete_reason", "scan_failure_reason"} <= (
            repositories_columns
        )

        session_fks = inspector.get_foreign_keys("sessions")
        assert any(fk["referred_table"] == "users" for fk in session_fks)

        remediation_fks = inspector.get_foreign_keys("remediations")
        assert any(fk["referred_table"] == "repositories" for fk in remediation_fks)
        assert any(fk["referred_table"] == "users" for fk in remediation_fks)

        remediation_findings_fks = inspector.get_foreign_keys("remediation_findings")
        assert any(fk["referred_table"] == "remediations" for fk in remediation_findings_fks)
        assert any(fk["referred_table"] == "findings" for fk in remediation_findings_fks)
    finally:
        engine.dispose()

    command.downgrade(config, "base")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) == {"alembic_version"}
    finally:
        engine.dispose()

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {"users", "sessions", "remediations", "remediation_findings"} <= tables
    finally:
        engine.dispose()

    command.downgrade(config, "base")
