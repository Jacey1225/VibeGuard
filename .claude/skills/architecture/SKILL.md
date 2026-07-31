---
name: architecture
description: Mandatory file/code architecture conventions for VibeGuard (Python). Consult before creating new files/modules, restructuring code, or when a change touches more than one module. Applies for the entire life of the project, not just initial setup.
user-invocable: true
---

# Architecture — File & Code Structure Standards

TRIGGER: read this before creating a new module, moving code between
files, adding a new package/subpackage, or whenever a change spans more
than one file. Also consult it as part of [feature-approval](../feature-approval/SKILL.md)
when scoping where a new feature's code will live.

## Layout

- `src/vibeguard/` — the installable package (src-layout, not a flat
  package at repo root). Prevents accidentally importing from the repo
  root instead of the installed package during tests.
- `tests/` — mirrors `src/vibeguard/` 1:1. A module at
  `src/vibeguard/engine/scanner.py` has its tests at
  `tests/engine/test_scanner.py`. If you can't find where a test belongs,
  that's a sign the module it's testing isn't scoped clearly yet.
- `pyproject.toml` — single source of truth for dependencies, tool config
  (ruff, mypy, pytest). No scattered `setup.py`/`setup.cfg`/`requirements*.txt`.

## Module boundaries

Layers, in dependency order (an inner layer never imports an outer one):

1. **core/domain** — pure logic: rule definitions, finding data models,
   severity scoring. No I/O, no network, no subprocess.
2. **adapters** — anything touching the outside world: filesystem
   walking, subprocess calls (external scanners, git), HTTP clients
   (GitHub API, pentest-mode probing), the database. Each external
   system gets its own adapter module — don't let subprocess/HTTP/DB
   calls leak into core. Depends only on core.
3. **engine** — orchestrates core logic against real input obtained via
   adapters (file trees, ASTs, HTTP responses, subprocess output,
   database rows). Depends on core and adapters; doesn't depend on
   cli/api/reporting.
4. **cli / api / reporting** — the outermost interface layer: CLI
   argument parsing and HTTP route/request handling, plus output
   formatting (JSON, terminal, SARIF, HTTP response bodies). Depends on
   everything below; nothing depends on it.

If you're about to write an import that points "up" this list (e.g. core
importing from cli), stop — that's the signal the code is in the wrong
module.

## Naming

- Modules/functions/variables: `snake_case`.
- Classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`, defined once near the top of the module
  that owns them (or in a `constants.py` only if genuinely shared across
  modules — don't create it preemptively).

## Single-purpose cascade (file → class → function)

This is a hard rule, not a soft smell — it takes precedence over the
size heuristics below whenever the two seem to disagree.

- **File**: has exactly one main purpose, statable in a single sentence
  without "and". A file's purpose should be recoverable from its name
  alone (e.g. `sql_injection_rule.py` detects SQL injection — nothing
  else). If you can't summarize a file's contents that way, it needs to
  split.
- **Class**: every class defined in a file must either directly
  implement that file's stated purpose, or be a sub-purpose the file's
  purpose can't be fulfilled without (e.g. a small result/data class
  that only exists to carry that file's output, or a private helper
  class scoped to that one job). A class serving an unrelated purpose —
  even a small, convenient one — belongs in its own file regardless of
  size.
- **Function**: performs exactly one operation. If describing what it
  does needs "and" or "then" ("validates and transforms", "fetches then
  caches"), it's more than one function — extract each step into its own
  single-operation function and have the caller sequence them. This
  holds at the lowest level too: a helper called from exactly one place
  still does only one thing.

## Size & complexity smells

- A module pushing past ~400-500 lines, or a function needing more than
  ~4 levels of indentation, is a signal that the single-purpose cascade
  above is already being violated somewhere — find the seam and split
  it, don't just note the smell and move on.
- No circular imports. If two modules need each other, the shared bit
  belongs in a lower layer (usually core).

## Dependencies

- New third-party dependency → add to `pyproject.toml` with a pinned
  compatible version, and briefly justify it against
  [code-security](../code-security/SKILL.md)'s dependency rules before
  adding it (this is part of the feature-approval scoping step for
  anything that introduces one).
- Absolute imports within the package (`from vibeguard.engine import
  scanner`), never relative wildcard imports.
