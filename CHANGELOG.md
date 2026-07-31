# Changelog

## Unreleased

### Added

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
