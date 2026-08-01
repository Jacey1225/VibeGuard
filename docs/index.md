# VibeGuard

A security vulnerability scanning and code-review tool. Python, FastAPI, Postgres.

## What it does

VibeGuard takes in a public GitHub repository, stores its contents, and
scans it for security issues.

The pipeline today:

1. **Submit** a public GitHub repository URL (`POST /repositories`).
2. **Validate** — the URL must be a well-formed `github.com/<owner>/<repo>`
   reference, and the repository must actually be public.
3. **Clone and store** — VibeGuard shallow-clones the repository and
   persists every included file's contents to Postgres, under
   configurable resource limits (oversized or binary files are skipped
   and noted, not fatal).
4. **Scan** (`POST /repositories/{id}/scan`) — cheap local pattern
   matching runs over every stored file against 10 OWASP-aligned
   vulnerability categories; only files that match get sent to an LLM
   (DeepSeek V3.1 via OpenRouter) to confirm the finding and write
   remediation guidance.
5. **Review findings** (`GET /repositories/{id}/findings`) — every
   confirmed finding, worst severity first.
6. **Remediate** (`POST /repositories/{id}/remediate`) — for a scanned
   repository, generate an LLM-proposed fix per findings-bearing file.
   Requires GitHub OAuth login.
7. **Review and decide** (`GET /repositories/{id}/remediations`,
   `POST /remediations/{id}/approve` / `.../reject`) — review each
   proposal's diff, then approve (pushes a direct commit to the
   repository's default branch via the GitHub Contents API — no PR,
   no CI gate) or reject.

See [Getting Started](getting-started.md) to run it locally, or the
[API Reference](api.md) for the full request/response shapes and a
note on what scanning sends to a third-party LLM provider.
