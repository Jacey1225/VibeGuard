# API Reference

## `POST /repositories`

Submit a public GitHub repository for intake. The request blocks until
the whole sequence finishes — validate, clone, store, mark
scan-pending — and returns the resulting repository record. There is no
background job or polling endpoint; this is intentional for the current
scope.

### Request body

```json
{
  "repo_url": "https://github.com/octocat/Hello-World"
}
```

`repo_url` must be a `https://github.com/<owner>/<repo>` URL — no other
host, no embedded credentials, no query string or fragment.

### Response body

```json
{
  "id": 1,
  "source_url": "https://github.com/octocat/Hello-World",
  "owner": "octocat",
  "name": "Hello-World",
  "status": "scan_pending_implementation",
  "rejection_reason": null,
  "files_truncated": false,
  "truncation_reason": null,
  "total_files_stored": 2,
  "total_files_skipped": 0,
  "total_bytes_stored": 21,
  "created_at": "2026-07-31T00:14:35.697317-07:00",
  "updated_at": "2026-07-31T00:14:35.697317-07:00"
}
```

### Status values

| `status` | Meaning |
|---|---|
| `pending` | Row created; validation/clone still in progress (never observed in the response — the request blocks until a terminal state). |
| `scan_pending_implementation` | Stored successfully, not yet scanned. |
| `scanning` | A scan is in progress (transient — never observed in a response, since `POST /scan` blocks until it finishes). |
| `scanned` | A scan completed. See `GET /findings` for results, and `scan_incomplete` below. |
| `scan_failed` | Every attempted LLM call during the scan failed — no findings could be confirmed. See `scan_failure_reason`. |
| `rejected` | Intake stopped short. See `rejection_reason`. |

### Rejection reasons

| `rejection_reason` | Meaning |
|---|---|
| `not_public_or_not_found` | The repository is private, or doesn't exist. |
| `repo_too_large` | GitHub's reported size clears the configured budget before any clone was attempted. |
| `clone_failed` | `git clone` exited non-zero (repo-specific problem). |
| `clone_timeout` | The clone didn't finish within the configured timeout. |

### HTTP status codes

| Condition | Row created? | HTTP status |
|---|---|---|
| Malformed URL / non-github host / embedded credentials | No | `422` |
| GitHub API unreachable/timeout | No | `502` |
| Private, nonexistent, oversized, clone-failed, or clone-timeout | Yes (`rejected`) | `201` |
| Success, with or without truncation | Yes (`scan_pending_implementation`) | `201` |
| Unexpected server error | — | `500` |

A row is only ever created once the GitHub API has answered about the
*specific* repository being submitted — a malformed URL or an
unreachable GitHub API never persists anything.

### Truncation

`files_truncated` is independent of `status`: a repository can reach
`scan_pending_implementation` and still have `files_truncated: true` if
the file-count or total-size budget was hit partway through — the files
seen before the limit are kept, not discarded. `truncation_reason` holds
the specific limit that triggered it.

## `POST /repositories/{id}/scan`

Run a vulnerability scan against a repository already stored via
intake. The request **blocks for the entire scan** — every flagged file
is confirmed via an LLM call before the response returns. See
[Data handling](#data-handling) below for what that means for the
repository's content, and the note on request duration.

Calling this a second time **replaces** the repository's prior
findings — there's no scan history in the current version; `GET
/findings` always reflects the latest scan.

### Response body

Same shape as `POST /repositories`' response (the repository record),
with the scan-relevant fields populated:

```json
{
  "id": 1,
  "status": "scanned",
  "scan_incomplete": false,
  "scan_incomplete_reason": null,
  "scan_failure_reason": null,
  "...": "..."
}
```

### HTTP status codes

| Condition | HTTP status |
|---|---|
| No repository with this id | `404` |
| Repository isn't in a scannable status (still cloning, or `rejected`) | `409` |
| Scan runs (regardless of outcome — `scanned` or `scan_failed`) | `200` |

### Incomplete scans

`scan_incomplete` is independent of `status`: a scan can reach
`scanned` and still be incomplete if either the per-scan LLM-call cap
was reached (more files were flagged than the configured budget
allows) or some — but not all — LLM calls failed. `scan_incomplete_reason`
describes which. If *every* attempted LLM call failed, the repository
lands on `scan_failed` instead (see above), not `scanned` with
`scan_incomplete: true` — a total outage should never look like "we
scanned it and it's clean."

### Known limitation: request duration

Flagged files are confirmed with bounded concurrency, but a large repo
can still legitimately take several minutes on a single request — this
is a deliberate v1 trade-off (see the project's development plan for
the reasoning). Any reverse proxy or client calling this endpoint needs
a generous timeout.

## `GET /repositories/{id}/findings`

Return every finding for a repository, worst severity first (ties
broken by file path, then line number).

### Response body

```json
{
  "findings": [
    {
      "id": 1,
      "category": "injection",
      "severity": "high",
      "source": "heuristic_confirmed",
      "title": "SQL injection via f-string interpolation",
      "description": "User-controlled input is interpolated directly into a SQL query string.",
      "remediation": "Use a parameterized query instead of string interpolation.",
      "relative_path": "app/db.py",
      "line_number": 42,
      "model": "deepseek/deepseek-chat-v3.1",
      "created_at": "2026-07-31T00:20:00.000000-07:00"
    }
  ]
}
```

`source` is `heuristic_confirmed` for LLM-reviewed findings, or
`heuristic_only` for the one non-LLM finding VibeGuard produces itself
(dependency-manifest presence — see below). `model` is `null` for
`heuristic_only` findings.

### HTTP status codes

| Condition | HTTP status |
|---|---|
| No repository with this id | `404` |
| Findings returned (empty list if none) | `200` |

## `POST /snippets`

Submit plain-text code for scanning -- the counterpart to `POST
/repositories` for callers who have source code in hand rather than a
GitHub URL. No external service call is involved, so the request
returns immediately.

### Request body

```json
{
  "content": "password = \"admin\"",
  "filename": "app.py"
}
```

`filename` is optional and purely a display label attached to any
findings produced -- it has no effect on which heuristics run (they're
content-based, not extension-based). Omit it and a default filename is
used instead.

### Response body

```json
{
  "id": 1,
  "filename": "app.py",
  "size_bytes": 19,
  "status": "scan_pending",
  "rejection_reason": null,
  "scan_incomplete": false,
  "scan_incomplete_reason": null,
  "scan_failure_reason": null,
  "created_at": "2026-08-01T00:14:35.697317-07:00",
  "updated_at": "2026-08-01T00:14:35.697317-07:00"
}
```

### Status values

| `status` | Meaning |
|---|---|
| `pending` | Never observed in the response -- validation is synchronous. |
| `scan_pending` | Stored successfully, not yet scanned. |
| `scanning` | A scan is in progress (transient -- never observed in a response). |
| `scanned` | A scan completed. See `GET /findings` for results, and `scan_incomplete` below. |
| `scan_failed` | Every attempted LLM call during the scan failed. See `scan_failure_reason`. |
| `rejected` | Intake stopped short. See `rejection_reason`. |

### Rejection reasons

| `rejection_reason` | Meaning |
|---|---|
| `empty_content` | `content` was empty or whitespace-only. |
| `too_large` | `content` exceeds the configured per-file size budget (`max_file_size_bytes` -- the same limit that bounds one repository file's content, not a separate setting). A too-large submission is rejected without its content being stored. |

### HTTP status codes

| Condition | HTTP status |
|---|---|
| Missing `content` field | `422` |
| Submitted (accepted or rejected) | `201` |

### Known limitation: request body size

Unlike repository intake (which only ever receives a URL string), the
full `content` string arrives in the request body before any size
check runs -- there's no framework-level body-size limit in front of
this endpoint today, so a very large request body is still fully
buffered before `max_file_size_bytes` gets a chance to reject it. This
is the same characteristic every POST endpoint in this API already has
(no route has an ASGI-level body cap), not something specific to
snippets.

## `POST /snippets/{id}/scan`

Run a vulnerability scan against a snippet already stored via intake.
Reuses the same heuristic-then-LLM engine as `POST
/repositories/{id}/scan` (see `engine/llm_confirmation.py`), minus the
dependency-manifest check -- that heuristic looks for a manifest or
lockfile *filename* across a whole file tree, which doesn't apply to a
single pasted blob. The request **blocks for the whole scan**, the same
trade-off `POST /repositories/{id}/scan` makes.

Calling this a second time **replaces** the snippet's prior findings.

### Response body

Same shape as `POST /snippets`' response, with the scan-relevant fields
populated -- see `POST /repositories/{id}/scan` above for what
`scan_incomplete` means.

### HTTP status codes

| Condition | HTTP status |
|---|---|
| No snippet with this id | `404` |
| Snippet isn't in a scannable status (`rejected`) | `409` |
| Scan runs (regardless of outcome -- `scanned` or `scan_failed`) | `200` |

## `GET /snippets/{id}/findings`

Return every finding for a snippet, worst severity first (ties broken
by file path, then line number) -- identical ordering and response
shape to `GET /repositories/{id}/findings` above.

### HTTP status codes

| Condition | HTTP status |
|---|---|
| No snippet with this id | `404` |
| Findings returned (empty list if none) | `200` |

## `GET /auth/github/login`

Redirects the browser to GitHub's OAuth consent screen, requesting
`public_repo` scope only. Sets a short-lived, httponly `state` cookie
(`vibeguard_oauth_state`) used to protect the callback below against
CSRF — not consumed by API clients directly.

| HTTP status | Meaning |
|---|---|
| `307` | Redirect to `github.com/login/oauth/authorize`. |

## `GET /auth/github/callback`

GitHub redirects here after the user approves (or denies) access. The
`state` query param is compared to the `vibeguard_oauth_state` cookie
**before any GitHub call fires** — a mismatch or missing cookie is
rejected immediately. On success, the user is created or updated
(keyed on GitHub's numeric user id, not login name, which can change),
a new session is issued, and the browser is redirected to
`{frontend_redirect_base_url}#session_token=<raw token>` — the token
is delivered in a URL **fragment**, which browsers never send to a
server or include in `Referer` headers.

The returned session token is a bearer token: send it back as
`Authorization: Bearer <token>` on every remediation route below, not
as a cookie (deliberately — bearer-in-header is never ambiently
attached to cross-site requests, so CSRF doesn't apply to those routes
at all).

### HTTP status codes

| Condition | HTTP status |
|---|---|
| Missing or mismatched `state` | `401` |
| GitHub rejected the code, or returned an unparseable response | `401` |
| GitHub's OAuth endpoints unreachable | `502` |
| Success | `307` (redirect with `#session_token=...`) |

## `POST /auth/logout`

Deletes the caller's session row, revoking their bearer token
immediately. Requires `Authorization: Bearer <token>`.

| Condition | HTTP status |
|---|---|
| Missing/invalid/expired token | `401` |
| Session deleted | `204` |

## `POST /repositories/{id}/remediate`

Requires authentication. Generates a proposed fix for every
findings-bearing file in a repository that has completed a scan — one
LLM call per **file** (all of that file's findings are addressed in a
single call), not one call per finding. Blocks for the whole request,
the same trade-off as `POST /scan`.

### Response body

```json
{
  "remediations": [ "...", "see GET /repositories/{id}/remediations below" ],
  "attempted": 3,
  "succeeded": 2,
  "files_over_cap": 0
}
```

`attempted` and `succeeded` make partial failure visible: a per-file
generation failure (LLM unavailable, unparseable response) is logged
and skipped, not a hard failure of the whole request. `files_over_cap`
counts files that exceeded `max_llm_calls_per_remediation` and were
never attempted.

### HTTP status codes

| Condition | HTTP status |
|---|---|
| Missing/invalid/expired token | `401` |
| No repository with this id | `404` |
| Repository hasn't completed a scan (`status != scanned`) | `409` |
| Generation ran (regardless of per-file outcomes) | `200` |

## `GET /repositories/{id}/remediations`

Requires authentication. Returns every remediation for a repository,
newest first.

### Response body

```json
{
  "remediations": [
    {
      "id": 1,
      "repository_id": 1,
      "relative_path": "app/db.py",
      "status": "proposed",
      "original_content": "...",
      "proposed_content": "...",
      "diff_text": "--- a/app/db.py\n+++ b/app/db.py\n...",
      "summary": "Parameterized the query to prevent SQL injection.",
      "model": "deepseek/deepseek-chat-v3.1",
      "introduces_new_heuristic_hits": false,
      "new_heuristic_hit_summary": null,
      "push_target_branch": null,
      "pushed_commit_sha": null,
      "push_failure_reason": null,
      "decided_at": null,
      "decided_by_user_id": null,
      "decision_reason": null,
      "created_at": "2026-08-01T00:00:00.000000-07:00"
    }
  ]
}
```

`introduces_new_heuristic_hits` is a safety-net signal, not a gate: it
flags when re-running VibeGuard's own heuristics against
`proposed_content` newly matches a category the fix wasn't asked to
address (e.g. a "fix" that introduces a hardcoded secret) —
`new_heuristic_hit_summary` names the category. Always review the diff;
this signal can both false-positive and miss real regressions.

### Status values

| `status` | Meaning |
|---|---|
| `proposed` | Awaiting review. |
| `rejected` | A reviewer rejected it. Terminal. |
| `pushed` | Approved and successfully pushed to GitHub. Terminal. |
| `push_failed` | Approved, but the push failed. **Retryable** — re-`approve` to try again. |

### HTTP status codes

| Condition | HTTP status |
|---|---|
| Missing/invalid/expired token | `401` |
| No repository with this id | `404` |
| Remediations returned (empty list if none) | `200` |

## `POST /remediations/{id}/approve`

Requires authentication. Approves a remediation and pushes it to the
target GitHub repository via the Contents API — a direct commit, no
pull request. Uses the **approving (authenticated) user's own** stored
GitHub token, never the token of whoever originally submitted the
repository for intake (intake has no user concept at all).

### Request body

```json
{
  "target_branch": null
}
```

`target_branch` is optional — omit or pass `null` to push to the
repository's current default branch, fetched fresh from GitHub at
approval time (never cached from proposal time).

### Push mechanics

The target branch and the file's current blob `sha` are both fetched
fresh, immediately before the write. If GitHub's write rejects the
`sha` (409 — the file changed upstream since this proposal was
generated), the remediation is marked `push_failed` /
`stale_sha_conflict` and the API returns `409` — **no automatic merge
is ever attempted**; regenerate the remediation against the file's
current content and try again.

### HTTP status codes

| Condition | HTTP status |
|---|---|
| Missing/invalid/expired token | `401` |
| No remediation with this id | `404` |
| Already `pushed` or `rejected` (terminal) | `409` |
| Target file changed upstream since generation (`stale_sha_conflict`) | `409` |
| Approving user's token lacks `public_repo` scope, or GitHub denies write access | `403` |
| GitHub's API unreachable or failed unexpectedly | `502` |
| Pushed successfully | `200` |

## `POST /remediations/{id}/reject`

Requires authentication. Rejects a proposed or previously-`push_failed`
remediation — no GitHub call is made.

### Request body

```json
{
  "decision_reason": "not applicable to this deployment"
}
```

`decision_reason` is optional free text.

### HTTP status codes

| Condition | HTTP status |
|---|---|
| Missing/invalid/expired token | `401` |
| No remediation with this id | `404` |
| Already `pushed` or `rejected` (terminal) | `409` |
| Rejected | `200` |

## Data handling

Scanning uses a hybrid approach: cheap pattern-matching runs over every
stored file locally, and **only files that match a pattern** are sent
to a third-party LLM provider (OpenRouter, routing to DeepSeek) for
confirmation and remediation guidance. Plain-text snippets (`POST
/snippets`) go through the identical hybrid pipeline, treated as a
single file. This means:

- Not every file's content leaves VibeGuard's infrastructure — only the
  subset flagged by the local heuristics.
- Vulnerability category 9 (vulnerable dependencies) is handled without
  any LLM call at all — VibeGuard only confirms a manifest/lockfile is
  present and points at a dedicated SCA tool (pip-audit, npm audit,
  osv-scanner) as a follow-up; it doesn't match dependency versions
  against CVEs itself.
- Each LLM call is a single, independent request — no conversation
  history or cross-file context is shared between calls, even within
  the same scan.

Remediation raises the stakes: the scan engine's output is prose a
human reads, but a successfully prompt-injected remediation could be
pushed to a real branch as if it were a legitimate fix. Beyond the
`<FILE_CONTENT>` untrusted-data delimiting reused from scanning, the
remediation prompt explicitly restricts the model to changing only
what the listed findings require (no unrelated edits), and every
proposal is re-checked against VibeGuard's own heuristics before
being shown to a reviewer (`introduces_new_heuristic_hits`, above).
The human diff review at approval time remains the real gate — there
is no PR, no CI, no second check on GitHub's side, since approval
pushes directly to the target branch.
