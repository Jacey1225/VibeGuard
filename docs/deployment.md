# Deployment

VibeGuard's backend and frontend deploy to two different platforms, not
one:

- **Frontend** (`frontend/`, a Vite/React app) → [Vercel](https://vercel.com).
  A standard static/SPA deploy — Vercel is built for exactly this.
- **Backend** (`src/vibeguard`, FastAPI + Postgres) → [Render](https://render.com).
  Render, not Vercel, because the backend needs things Vercel's
  serverless functions don't provide: a `git` binary for repository
  intake (`POST /repositories` shells out to `git clone`), requests
  that can legitimately block for several minutes (`POST
  /repositories/{id}/scan`), and a persistent Postgres connection
  rather than a per-invocation cold start.

Deploy the backend first — the frontend needs its URL.

## Backend on Render

### Before you start

Render will prompt you for these during setup; have them ready:

- An [OpenRouter](https://openrouter.ai) API key (`OPENROUTER_API_KEY`)
  — required even if you never touch remediation, since the scan engine
  needs it.
- A GitHub OAuth App's client ID and secret. Required by `Settings` at
  startup regardless of whether you use the login/remediation flow —
  see [Getting Started](getting-started.md#github-oauth-app-required-for-remediation-approvepush)
  for how to provision one. You won't have the callback URL yet (it
  depends on Render's assigned URL); come back and fill it in after
  first deploy, per the note below.
- A Fernet encryption key:
  `./.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`

### Deploy

1. Push this repo to GitHub (if not already).
2. Render dashboard → **New** → **Blueprint** → select the repo. Render
   reads `render.yaml` from the repo root and provisions a web service
   (`vibeguard-api`) plus a managed Postgres instance (`vibeguard-db`).
3. Render prompts for every env var marked `sync: false` in
   `render.yaml`. For `VIBEGUARD_GITHUB_OAUTH_REDIRECT_URI` and
   `VIBEGUARD_FRONTEND_REDIRECT_BASE_URL`, enter a placeholder for now
   (e.g. `http://localhost`) — you'll update both after the frontend is
   deployed, below.
4. Deploy. The build runs `pip install -e .`; the start command runs
   `alembic upgrade head` (applying the schema to the fresh database)
   before starting `uvicorn`.
5. Once live, note the assigned URL (`https://vibeguard-api-xxxx.onrender.com`
   or similar). Go back to the service's **Environment** settings and
   set `VIBEGUARD_GITHUB_OAUTH_REDIRECT_URI` to
   `<that URL>/auth/github/callback` — then update the same callback
   URL on the GitHub OAuth App itself (**Settings → Developer settings
   → OAuth Apps**), since GitHub rejects a mismatch.

### Plan/tier notes

- `render.yaml` defaults the web service to `starter` and the database
  to `free`. Render's **free** web service tier spins down after 15
  minutes of inactivity and takes about a minute to cold-start on the
  next request — workable for trying things out, but combined with a
  multi-minute scan request, the first request after idle time will be
  slow. Switch the service `plan` to something paid if that matters for
  your use.
- `alembic upgrade head` re-runs on every boot. That's safe (idempotent,
  tracked per-revision) for one instance; if you ever scale to multiple
  instances, move it to a separate pre-deploy step instead.

## Frontend on Vercel

1. Vercel dashboard → **Add New** → **Project** → import this repo.
2. Before deploying, click **Edit** next to **Root Directory** and set
   it to `frontend`. Vercel auto-detects the Vite framework preset (`npm
   run build`, output `dist`) once the root directory is set — no
   `vercel.json` needed.
3. Under **Environment Variables**, add `VITE_VIBECHECK_API_URL` set to
   the Render backend's URL from above (no trailing slash). This is a
   build-time Vite env var — `frontend/.env.local` isn't committed to
   git (see `frontend/.gitignore`), so it has to be set here, not
   inherited from the repo.
4. Deploy.

## Wire them together

Once both are live:

- On Render, set `VIBEGUARD_CORS_ALLOWED_ORIGINS` to the Vercel
  project's URL (`https://<project>.vercel.app`). Without this, every
  request from the frontend fails CORS — see
  [Getting Started](getting-started.md#run-the-api). Comma-separate
  multiple values if you also want to allow a custom domain.
  Vercel issues a distinct URL per preview deployment (e.g. per PR);
  each one needs adding individually if you want previews to work
  against the deployed backend, or just test previews against
  `localhost:8000` instead.
- On Render, set `VIBEGUARD_FRONTEND_REDIRECT_BASE_URL` to the same
  Vercel URL — this is where the GitHub OAuth callback redirects the
  browser with the session token (see [API Reference](api.md#get-authgithubcallback)).

### Sanity check

```bash
curl https://<your-render-service>.onrender.com/docs   # 200 = backend is up
```

Then open the Vercel URL in a browser and submit a repository through
the composer — it should hit the real `/repositories` and `/scan`
endpoints (see `frontend/README.md` for which parts of the UI are still
fixture-driven simulation rather than wired to the live API).
