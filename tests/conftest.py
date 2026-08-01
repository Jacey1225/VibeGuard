"""Shared fixtures: a local bare git repo, a mocked GitHub client, and Postgres."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
from pytest_postgresql import factories
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# The Homebrew Postgres@17 install isn't on PATH by default in this
# environment; pytest-postgresql needs pg_ctl/initdb/postgres to spin up
# its own ephemeral cluster per test session.
os.environ["PATH"] = os.pathsep.join(
    filter(None, ["/opt/homebrew/opt/postgresql@17/bin", os.environ.get("PATH")])
)

from vibeguard.adapters.config.settings import Settings  # noqa: E402
from vibeguard.adapters.db.models import Base  # noqa: E402

postgresql_proc = factories.postgresql_proc()
postgresql_conn = factories.postgresql("postgresql_proc")

# A fixed, valid Fernet key for tests -- not a real secret, generated
# once via Fernet.generate_key() for deterministic test fixtures.
FERNET_TEST_KEY = "lvk_pkjO7PGb7TsXVDj9B59YXFJTAI8nO_gyK1nGLd4="

# Every Settings field with no default, satisfied with test-only
# placeholder values -- shared across tests that construct a Settings
# instance directly instead of via `settings_factory` (which also
# needs a real `database_url`, so it doesn't reuse this as-is).
REQUIRED_SETTINGS_KWARGS: dict[str, object] = {
    "database_url": "postgresql+psycopg://localhost/db",
    "openrouter_api_key": "test-openrouter-key",
    "github_oauth_client_id": "test-oauth-client-id",
    "github_oauth_client_secret": "test-oauth-client-secret",
    "github_oauth_redirect_uri": "http://localhost:8000/auth/github/callback",
    "frontend_redirect_base_url": "http://localhost:3000",
    "token_encryption_key": FERNET_TEST_KEY,
}


@pytest.fixture
def local_bare_repo(tmp_path: Path) -> Path:
    """A local bare git repo with a small committed tree, used as a clone source.

    Never hits real GitHub, per testing-standards.
    """
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    _run_git(["init", "-q"], cwd=work_dir)
    _run_git(["config", "user.email", "test@example.com"], cwd=work_dir)
    _run_git(["config", "user.name", "Test"], cwd=work_dir)

    (work_dir / "README.md").write_text("hello world\n")
    (work_dir / "src").mkdir()
    (work_dir / "src" / "app.py").write_text("print('hi')\n")

    _run_git(["add", "-A"], cwd=work_dir)
    _run_git(["commit", "-q", "-m", "initial"], cwd=work_dir)

    bare_dir = tmp_path / "bare.git"
    _run_git(["clone", "-q", "--bare", str(work_dir), str(bare_dir)])
    return bare_dir


def _run_git(args: list[str], cwd: Path | None = None) -> None:
    # Test-fixture setup only: fixed args, no untrusted input, PATH is
    # this machine's own -- unlike adapters/github/clone.py, which
    # resolves an absolute path for the real request-handling path.
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)  # noqa: S603, S607


def make_mock_http_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> httpx.Client:
    """Build an httpx.Client backed by a MockTransport, for network-free tests."""
    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture
def db_engine(postgresql_conn) -> Iterator[Engine]:
    """A SQLAlchemy engine bound to pytest-postgresql's ephemeral instance."""
    info = postgresql_conn.info
    url = f"postgresql+psycopg://{info.user}@{info.host}:{info.port}/{info.dbname}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """A request-scoped session against the ephemeral test database."""
    session_factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def settings_factory(db_engine: Engine) -> Callable[..., Settings]:
    """Build a Settings instance pointed at the test database, with overrides."""

    def _build(**overrides: object) -> Settings:
        defaults: dict[str, object] = {
            **REQUIRED_SETTINGS_KWARGS,
            "database_url": str(db_engine.url),
        }
        return Settings(**{**defaults, **overrides})  # type: ignore[arg-type]

    return _build
