# Getting Started

## Requirements

- Python 3.12+
- A running Postgres instance
- An [OpenRouter](https://openrouter.ai) API key (for the scan and
  remediation steps)
- A GitHub OAuth App (for the remediation approve/push flow — see
  below)

## Install

```bash
python3.12 -m venv .venv
./.venv/bin/pip install -e ".[dev]"
```

## Configure

Configuration is read from `VIBEGUARD_*` environment variables (see
`src/vibeguard/adapters/config/settings.py` for the full list and
defaults), with one deliberate exception — the OpenRouter key uses its
own conventional variable name, not the `VIBEGUARD_` prefix. At
minimum:

```bash
export VIBEGUARD_DATABASE_URL="postgresql+psycopg://user@host:port/dbname"
export OPENROUTER_API_KEY="sk-or-..."
```

### GitHub OAuth App (required for remediation approve/push)

The remediation feature (generating and pushing fixes) needs its own
GitHub OAuth App, separate from the unauthenticated GitHub access
intake/scanning use:

1. On GitHub: **Settings → Developer settings → OAuth Apps → New OAuth
   App**.
2. Set the **Authorization callback URL** to
   `http://localhost:8000/auth/github/callback` (adjust host/port for
   your deployment).
3. Note the generated **Client ID** and generate a **Client secret**.

```bash
export VIBEGUARD_GITHUB_OAUTH_CLIENT_ID="..."
export VIBEGUARD_GITHUB_OAUTH_CLIENT_SECRET="..."
export VIBEGUARD_GITHUB_OAUTH_REDIRECT_URI="http://localhost:8000/auth/github/callback"
export VIBEGUARD_FRONTEND_REDIRECT_BASE_URL="http://localhost:5173"
```

Also generate a `token_encryption_key` — this encrypts every stored
GitHub OAuth token at rest (via [Fernet](https://cryptography.io)):

```bash
export VIBEGUARD_TOKEN_ENCRYPTION_KEY="$(./.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
```

Generate this once and keep it stable — rotating it invalidates every
already-encrypted stored token (no rotation tooling exists yet, see
`docs/api.md`'s remediation section and the project's development plan
for what's out of scope in v1).

## Apply the database schema

```bash
./.venv/bin/alembic upgrade head
```

## Run the API

```bash
./.venv/bin/uvicorn vibeguard.api.main:app --reload
```

By default the API only accepts browser requests from
`http://localhost:5173` (Vite's default dev port, matching the frontend
below). Override this with a comma-separated
`VIBEGUARD_CORS_ALLOWED_ORIGINS` if the frontend runs elsewhere:

```bash
export VIBEGUARD_CORS_ALLOWED_ORIGINS="http://localhost:5173,https://app.example.com"
```

## Run the frontend

The product-facing UI lives in `frontend/`, a separate Node/Vite app:

```bash
cd frontend
npm install
npm run dev
```

It reads the backend's URL from `VITE_VIBECHECK_API_URL`
(`frontend/.env.local`), defaulting to `http://localhost:8000`. See
`frontend/README.md` for what is and isn't wired to the real API yet.

## Submit a repository

```bash
curl -X POST http://localhost:8000/repositories \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/octocat/Hello-World"}'
```

See the [API Reference](api.md) for the full response shape and status values.

## Scan it

```bash
curl -X POST http://localhost:8000/repositories/1/scan
curl http://localhost:8000/repositories/1/findings
```

This blocks until every flagged file has been reviewed — see
[API Reference](api.md#post-repositoriesidscan) for the duration
trade-off on large repositories, and what gets sent to the LLM
provider.

## Generate and push a remediation

Remediation routes require authentication. Log in via the browser (not
`curl` — it's a redirect-based OAuth flow):

```
http://localhost:8000/auth/github/login
```

After approving on GitHub, you land on
`{VIBEGUARD_FRONTEND_REDIRECT_BASE_URL}#session_token=<token>` — grab
`<token>` from the URL fragment and use it as a bearer token:

```bash
export TOKEN="<session_token from the redirect>"

curl -X POST http://localhost:8000/repositories/1/remediate \
  -H "Authorization: Bearer $TOKEN"
curl http://localhost:8000/repositories/1/remediations \
  -H "Authorization: Bearer $TOKEN"

# Review the diff_text in the response above, then:
curl -X POST http://localhost:8000/remediations/1/approve \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{}'
```

Approving pushes a direct commit to the repository's default branch —
there is no pull request and no second review step on GitHub's side.
Always review `diff_text` before approving. See
[API Reference](api.md#post-remediationsidapprove) for the full status
mapping, including the retryable `push_failed` state.

## Run the tests

Tests spin up an ephemeral local Postgres instance automatically
(`pytest-postgresql`) — no Docker or manual database setup required,
but Postgres binaries (`pg_ctl`, `initdb`, `postgres`) must be
reachable on `PATH`. Tests never call the real GitHub or OpenRouter
APIs.

```bash
./.venv/bin/pytest
./.venv/bin/ruff check src tests migrations
./.venv/bin/mypy src
```
