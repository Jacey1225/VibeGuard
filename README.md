# VibeGuard

A security vulnerability scanning and code-review tool. Python, FastAPI, Postgres.

## What it does

VibeGuard takes in a public GitHub repository, stores its contents, and
scans it for security issues. The first stage of that pipeline — intake —
is implemented: submit a repository URL, and VibeGuard validates it,
clones it, and persists every file's contents to Postgres for later
reference. The actual vulnerability-scanning rule engine is not yet
implemented; intake marks a repository `scan_pending_implementation`
once stored, ready for that engine to pick up.

## Setup

Requires Python 3.12+ and a running Postgres instance.

```bash
python3.12 -m venv .venv
./.venv/bin/pip install -e ".[dev]"
```

Configuration is via `VIBEGUARD_*` environment variables (see
`src/vibeguard/adapters/config/settings.py` for the full list and
defaults). At minimum:

```bash
export VIBEGUARD_DATABASE_URL="postgresql+psycopg://user@host:port/dbname"
```

Apply the database schema:

```bash
./.venv/bin/alembic upgrade head
```

## Running the API

```bash
./.venv/bin/uvicorn vibeguard.api.main:app --reload
```

## Submitting a repository

```bash
curl -X POST http://localhost:8000/repositories \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/octocat/Hello-World"}'
```

The request blocks until intake finishes (clone, filter, store) and
returns the repository's record, including its status:

- `scan_pending_implementation` — stored successfully, awaiting the real scan engine.
- `rejected` — see `rejection_reason` (`not_public_or_not_found`, `repo_too_large`, `clone_failed`, `clone_timeout`).

Only `https://github.com/<owner>/<repo>` URLs are accepted, and the
repository must be public.

## Running tests

Tests spin up an ephemeral local Postgres instance automatically
(`pytest-postgresql`) — no Docker or manual database setup required,
but Postgres binaries (`pg_ctl`, `initdb`, `postgres`) must be
reachable on `PATH`.

```bash
./.venv/bin/pytest
```

Lint and type-check:

```bash
./.venv/bin/ruff check src tests
./.venv/bin/mypy src
```

## Project conventions

Development standards for this repo (architecture, secure coding,
testing, documentation, feature approval, search/sort efficiency, and
the GitHub sync check) live in `.claude/skills/` and are indexed in
`CLAUDE.md`. They apply to every change, not just initial setup.
