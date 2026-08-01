# Development

## Project conventions

Every change in this repo — for its entire life, not just initial setup
— follows six mandatory standards, defined in `.claude/skills/` and
indexed in `CLAUDE.md`:

- **architecture** — file/module layout, layering (`core` → `adapters`
  → `engine` → `cli/api/reporting`), naming, single-purpose cascade.
- **code-security** — secure coding for VibeGuard's own code: subprocess
  safety, path containment, resource limits on untrusted input.
- **testing-standards** — pytest, coverage expectations, regression
  rules.
- **documentation-standards** — this site included: docstrings, README,
  changelog, and this MkDocs site all need to stay current.
- **feature-approval** — the plan-and-scope gate for new features (not
  bugfixes/refactors).
- **search-sort-efficiency** — data structure/algorithm choices for any
  search, lookup, or sort over findings/rules/files.

## Layout

```
src/vibeguard/
  core/             # pure logic, no I/O
    heuristics/          # regex pattern-matchers feeding the LLM confirmation step
    remediation_guidance/  # category-specific fix guidance fed into the remediation prompt
  adapters/         # filesystem, subprocess, HTTP, database
    llm/            # OpenRouter clients (scan confirmation, remediation generation)
    auth/           # GitHub OAuth client, token encryption, session tokens
    github/         # unauthenticated intake client + authenticated push client
  engine/           # orchestrates core logic via adapters
  api/              # FastAPI routes, schemas, app wiring

tests/        # mirrors src/vibeguard/ 1:1
migrations/   # Alembic migrations (ops tooling, not part of the package)
docs/         # this site
```

## Running checks

```bash
./.venv/bin/pytest
./.venv/bin/ruff check src tests migrations
./.venv/bin/mypy src
```

## Working on this site

```bash
./.venv/bin/pip install -e ".[docs]"
./.venv/bin/mkdocs serve
```

`mkdocs build --strict` must pass — broken internal links or nav
references fail the build rather than silently rendering a broken page.
