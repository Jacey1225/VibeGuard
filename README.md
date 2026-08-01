# VibeGuard

A security vulnerability scanning and code-review tool. Python, FastAPI, Postgres.

## What it does

VibeGuard takes in a public GitHub repository, stores its contents, and
scans it for security issues.

1. **Intake** — submit a repository URL; VibeGuard validates it, clones
   it, and persists every file's contents to Postgres.
2. **Scan** — a hybrid heuristic-then-LLM pipeline checks the stored
   files against 10 OWASP-aligned vulnerability categories. Cheap local
   pattern matching runs over every file; only files that match get
   sent to an LLM (DeepSeek V3.1 via OpenRouter) to confirm the finding
   and write remediation guidance. See [Data
   handling](docs/api.md#data-handling) for what that means for
   scanned code.
3. **Remediate** — for a scanned repository, generate an LLM-proposed
   fix per findings-bearing file, review the diff, and on approval push
   it directly to the repository's default branch on GitHub (via GitHub
   OAuth login and the Contents API — no PR, no CI gate; the diff
   review at approval time is the safety net).

## Setup

Requires Python 3.12+, a running Postgres instance, an
[OpenRouter](https://openrouter.ai) API key, and (for the remediation
approve/push flow) a GitHub OAuth App — see
[Getting Started](docs/getting-started.md#github-oauth-app-required-for-remediation-approvepush)
for how to provision one.

```bash
python3.12 -m venv .venv
./.venv/bin/pip install -e ".[dev]"
```

Configuration is via `VIBEGUARD_*` environment variables (see
`src/vibeguard/adapters/config/settings.py` for the full list and
defaults), plus one unprefixed exception. At minimum:

```bash
export VIBEGUARD_DATABASE_URL="postgresql+psycopg://user@host:port/dbname"
export OPENROUTER_API_KEY="sk-or-..."
```

The remediation feature additionally needs a GitHub OAuth App's
credentials and a Fernet encryption key for storing OAuth tokens at
rest — see
[Getting Started](docs/getting-started.md#github-oauth-app-required-for-remediation-approvepush)
for the full setup.

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

- `scan_pending_implementation` — stored successfully, ready to scan.
- `rejected` — see `rejection_reason` (`not_public_or_not_found`, `repo_too_large`, `clone_failed`, `clone_timeout`).

Only `https://github.com/<owner>/<repo>` URLs are accepted, and the
repository must be public.

## Scanning a repository

```bash
curl -X POST http://localhost:8000/repositories/1/scan
curl http://localhost:8000/repositories/1/findings
```

The scan request blocks until every flagged file has been reviewed —
see [API Reference](docs/api.md) for status values, the
`scan_incomplete` field, and a note on request duration for large
repositories.

## Generating and pushing a remediation

Remediation routes require a GitHub-authenticated session. Log in via
`http://localhost:8000/auth/github/login` in a browser, then use the
`session_token` from the redirect's URL fragment as a bearer token:

```bash
curl -X POST http://localhost:8000/repositories/1/remediate \
  -H "Authorization: Bearer $TOKEN"
curl http://localhost:8000/repositories/1/remediations \
  -H "Authorization: Bearer $TOKEN"
curl -X POST http://localhost:8000/remediations/1/approve \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{}'
```

Approving pushes a direct commit to GitHub — review each remediation's
`diff_text` before approving. See [Getting
Started](docs/getting-started.md#generate-and-push-a-remediation) for
the full walkthrough and [API Reference](docs/api.md) for the status
mapping.

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
./.venv/bin/ruff check src tests migrations
./.venv/bin/mypy src
```

## Full documentation

This README covers the basics. For the full docs site (API reference,
development guide):

```bash
./.venv/bin/pip install -e ".[docs]"
./.venv/bin/mkdocs serve
```

## Project conventions

Development standards for this repo (architecture, secure coding,
testing, documentation, feature approval, search/sort efficiency, and
the GitHub sync check) live in `.claude/skills/` and are indexed in
`CLAUDE.md`. They apply to every change, not just initial setup.
