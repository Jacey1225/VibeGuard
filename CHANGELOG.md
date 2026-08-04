# Changelog

## Unreleased

### Added

- Deployment config for Render (backend, `render.yaml` Blueprint) and
  docs for Vercel (frontend) — see `docs/deployment.md`. `Settings.database_url`
  now normalizes a bare `postgres://`/`postgresql://` URL (what every
  managed Postgres provider hands out) to `postgresql+psycopg://`, since
  SQLAlchemy's default driver for the bare scheme is psycopg2, which
  this project doesn't depend on — previously this would only surface
  as a crash on the first query, not at startup.
- CORS support (`CORSMiddleware`), previously entirely absent, so a
  browser-based frontend can call the API cross-origin at all. The
  allowed origin list is configurable via `VIBEGUARD_CORS_ALLOWED_ORIGINS`
  (comma-separated), defaulting to `http://localhost:5173` (Vite's
  default dev port) — never a wildcard, per the same misconfiguration
  this project's own `security_misconfiguration` heuristic flags in
  scanned code. Read directly from the environment
  (`load_cors_allowed_origins()` in `adapters/config/settings.py`)
  rather than through `Settings`, so registering it in `create_app()` —
  which must happen before the app starts serving — doesn't require
  every other `Settings` field (`database_url`, etc.) to be set first.

- `POST /repositories/{id}/scan` and `POST /snippets/{id}/scan` now
  accept an optional request body, `{"categories": [...]}`, selecting
  which of the 10 `VulnCategory` values to scan for. Filtering happens
  before the LLM-confirmation step (`core/heuristics/category_filter.py`):
  a file whose heuristic hits fall entirely outside the selected
  categories is never sent to the LLM at all, not just excluded from
  the output. The repository pipeline's dependency-manifest check
  (`vulnerable_dependencies`) is likewise skipped unless that category
  is selected. Omitting `categories` (or the whole body) scans every
  category, unchanged from before this field existed; an explicit empty
  list is rejected (`422`) rather than silently scanning nothing.
  Remediation isn't touched directly — it only ever proposes fixes for
  findings that exist, so it automatically inherits whatever category
  selection the preceding scan used.
- `POST /snippets`, `POST /snippets/{id}/scan`, `GET /snippets/{id}/findings`:
  a plain-text counterpart to the repository pipeline — submit code
  directly as a string (with an optional `filename` label) instead of a
  GitHub URL, then run it through the same heuristic-then-LLM scan
  engine. The budget-cap/LLM-confirmation/completion-status logic was
  extracted out of `vuln_scan.py` into `engine/llm_confirmation.py` so
  both pipelines share it rather than duplicating it. No
  dependency-manifest check here (that heuristic looks for a
  manifest/lockfile *filename* across a whole file tree, which doesn't
  apply to one pasted blob) and no remediation support yet. A snippet
  is bounded by the same `max_file_size_bytes` limit as one repository
  file — deliberately not a new setting — and an oversized submission
  is rejected without its content ever being persisted. Postgres schema
  additions via Alembic migration `0004_snippet_scan`: `snippets`,
  `snippet_findings` (reusing the existing `vuln_category`/`severity`/
  `finding_source` enums).
- GitHub OAuth login (`GET /auth/github/login`, `GET /auth/github/callback`,
  `POST /auth/logout`): the first authenticated flow in the app. Users
  authenticate via GitHub (`public_repo` scope only); their OAuth token
  is encrypted at rest (Fernet) and never returned to a client. Sessions
  are server-side (bearer token, `SHA-256` hash stored, never the raw
  token) with a fixed TTL — revocable by deleting the session row, not
  a stateless JWT, since this feature stores a live GitHub write
  credential. The OAuth `state` parameter is verified via an httponly
  cookie before any GitHub call fires, protecting the login redirect
  against CSRF; the issued session token is delivered to the frontend
  via a URL fragment, never logged or sent to the server.
- `POST /repositories/{id}/remediate`: for a scanned repository,
  generates a proposed fix for every findings-bearing file via
  DeepSeek V3.1 on OpenRouter — one call per file (all of that file's
  findings addressed together), full corrected file content back, not
  a diff (VibeGuard computes the diff itself). Category-specific
  remediation guidance (`core/remediation_guidance/`) is woven into
  each prompt, mirroring the heuristic engine's one-module-per-category
  shape but covering all 10 OWASP categories. Every proposal is
  re-checked by re-running VibeGuard's own heuristics against the
  *proposed* content, flagging (not blocking) any newly-introduced
  category as a safety-net signal for the reviewer. Requires
  authentication; blocks for the whole request like `/scan`, with the
  same admit-before-parallelize/bounded-concurrency shape.
- `GET /repositories/{id}/remediations`: every remediation for a
  repository, newest first, including the full diff and the model's
  own summary of the fix. Requires authentication.
- `POST /remediations/{id}/approve`: approves a remediation and pushes
  it directly to the target GitHub repository via the Contents API —
  no pull request, no CI gate; the human diff review at approval time
  is the whole safety net. Uses the *approving* (authenticated) user's
  own stored GitHub token, never the original intake submitter's
  (intake has no user concept). The target branch and the file's blob
  `sha` are both fetched fresh immediately before the write; a GitHub
  409 (the file changed upstream) marks the remediation `push_failed` /
  `stale_sha_conflict` and is never auto-merged. `push_failed` is
  retryable — re-approving retries the push from scratch with fresh
  fetches; `pushed`/`rejected` are terminal. Requires authentication.
- `POST /remediations/{id}/reject`: rejects a proposed or
  previously-`push_failed` remediation, with an optional reason.
  Requires authentication.
- Postgres schema additions via Alembic migration
  `0003_auth_and_remediation`: `users`, `sessions`, `remediations`
  (new `remediation_status`/`push_failure_reason` enums), and
  `remediation_findings` (a join table, not an implicit path match —
  `vuln_scan.py` hard-deletes and reinserts findings on every rescan,
  which would otherwise silently re-associate or orphan a remediation).
- `POST /repositories`: submit a public GitHub repository URL for intake.
  Validates the URL (must be a `github.com/<owner>/<repo>` reference),
  confirms the repository is public via the GitHub API, shallow-clones
  it, and persists every included file's contents to Postgres under
  configurable resource limits (max file size, max total size, max file
  count; oversized/binary files are skipped and noted, not fatal).
  Marks the repository `scan_pending_implementation` on success — the
  real vulnerability rule engine is a separate, not-yet-implemented
  feature. Rejected submissions (private/nonexistent repo, oversized
  repo, clone failure/timeout) are still persisted with a
  `rejection_reason`, so every submission attempt is queryable.
- Postgres schema (`repositories`, `repository_files`) via Alembic
  migration `0001_initial_schema`.
- MkDocs documentation site (`mkdocs.yml` + `docs/`, Material theme):
  overview, getting-started, API reference, and development pages.
  Run with `mkdocs serve` after `pip install -e ".[docs]"`.
- `POST /repositories/{id}/scan`: runs the vulnerability scan engine
  against a repository's stored files. A hybrid pipeline — cheap local
  regex heuristics run over every file across 6 directly-matchable
  OWASP categories plus a broader entry-point heuristic covering
  broken auth/access-control/logging; only files that match get one
  confirmation call each to DeepSeek V3.1 via OpenRouter (bounded
  concurrency, capped total calls per scan). Dependency/CVE scanning
  (category 9) is handled without an LLM call — VibeGuard flags
  manifest/lockfile presence and points at a dedicated SCA tool.
  Blocks for the whole scan; a second scan replaces prior findings.
  Total LLM-call failure marks the repository `scan_failed` rather than
  reporting a false-clean scan; partial failures or a reached call cap
  set `scan_incomplete` on an otherwise-`scanned` repository.
- `GET /repositories/{id}/findings`: every finding for a repository,
  worst severity first.
- Postgres schema additions via Alembic migration `0002_scan_engine`:
  `findings` table, extended `repository_status` enum
  (`scanning`/`scanned`/`scan_failed`), and `scan_incomplete` /
  `scan_incomplete_reason` / `scan_failure_reason` columns on
  `repositories`.
- Repository file-ingestion now reads admitted files concurrently
  (bounded thread pool) instead of sequentially — an amendment to the
  original intake feature, since disk reads there are I/O-bound.
