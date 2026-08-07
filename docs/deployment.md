# Deployment

VibeGuard's backend and frontend deploy separately, not as one unit:

- **Frontend** (`frontend/`, a Vite/React app) → a static host. Either
  a [Render Static Site](#frontend-on-a-render-static-site) or
  [Vercel](#frontend-on-vercel) work — both are a standard static/SPA
  deploy of the same `npm run build` output.
- **Backend** (`src/vibeguard`, FastAPI + Postgres) → [Render](https://render.com)
  as a web service, not a serverless platform (e.g. Vercel functions),
  because it needs things serverless doesn't provide: a `git` binary
  for repository intake (`POST /repositories` shells out to `git
  clone`), requests that can legitimately block for several minutes
  (`POST /repositories/{id}/scan`), and a persistent Postgres
  connection rather than a per-invocation cold start.

Order doesn't strictly matter — either can be deployed first with a
placeholder `VITE_VIBECHECK_API_URL`/CORS origin, then updated (and the
frontend redeployed, since Vite bakes that value in at build time) once
the other side's URL is known. Deploying the backend first avoids the
extra redeploy step, so that's the order below.

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

### Troubleshooting: OAuth sends users back to `localhost` after deploy

Symptom: a user completes GitHub's consent screen and lands on an
unreachable `http://localhost:8000/auth/github/callback?code=...&state=...`
instead of the deployed API. Cause: `VIBEGUARD_GITHUB_OAUTH_REDIRECT_URI`
on the Render service is still the placeholder from step 3 above — step 5
(setting it to the real `<service>.onrender.com/auth/github/callback`
URL, and updating the same callback URL on the GitHub OAuth App) was
skipped or reset. Fix: go back and do step 5. The authorization `code`
and `state` from the broken attempt are single-use and already expired,
so the user just needs to retry login after the value is corrected — no
data was lost.

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

## Frontend on a Render Static Site

1. Render dashboard → **New** → **Static Site** → select this repo.
2. Root Directory: `frontend`. Build Command: `npm install && npm run
   build`. Publish Directory: `dist` (relative to Root Directory).
3. Under **Environment Variables**, add `VITE_VIBECHECK_API_URL` set to
   the `vibeguard-api` Render service's URL (no trailing slash).
4. Deploy. Since Vite bakes `VITE_*` vars into the built JS at build
   time (not read at runtime), changing this env var later requires
   triggering a fresh manual deploy to take effect — it won't apply to
   an already-built bundle.

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

- On Render (backend), set `VIBEGUARD_CORS_ALLOWED_ORIGINS` to the
  frontend's URL (`https://<your-static-site>.onrender.com` or
  `https://<project>.vercel.app`). Without this, every request from the
  frontend fails CORS — see [Getting Started](getting-started.md#run-the-api).
  Comma-separate multiple values if you also want to allow a custom
  domain. If using Vercel, it issues a distinct URL per preview
  deployment (e.g. per PR); each one needs adding individually if you
  want previews to work against the deployed backend, or just test
  previews against `localhost:8000` instead.
- On Render (backend), set `VIBEGUARD_FRONTEND_REDIRECT_BASE_URL` to
  the same frontend URL — this is where the GitHub OAuth callback
  redirects the browser with the session token (see
  [API Reference](api.md#get-authgithubcallback)).

### Sanity check

```bash
curl https://<your-render-service>.onrender.com/docs   # 200 = backend is up
```

Then open the frontend's URL in a browser and submit a repository
through the composer — it should hit the real `/repositories` and
`/scan` endpoints (see `frontend/README.md` for which parts of the UI
are still fixture-driven simulation rather than wired to the live
API).
