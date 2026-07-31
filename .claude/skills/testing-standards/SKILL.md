---
name: testing-standards
description: Mandatory logic-testing standards for VibeGuard (pytest, coverage, regression rules). Consult whenever writing or changing any logic in src/vibeguard — new code needs tests before it's considered done. Applies for the entire life of the project.
user-invocable: true
---

# Testing Standards — Logic Testing for VibeGuard

TRIGGER: read whenever adding or changing logic under `src/vibeguard/`
(a new rule/check, a parser, a scoring function, a CLI command) or when
fixing a bug. Untested logic isn't done — it's in progress.

## Framework & layout

- `pytest`, tests under `tests/`, mirroring `src/vibeguard/` per
  [architecture](../architecture/SKILL.md).
- Test names: `test_<unit>_<scenario>_<expected_outcome>`, e.g.
  `test_sql_injection_rule_flags_string_concat_query`. A test name should
  tell you what broke without opening the file.
- One behavior per test. If a test needs "and" in its name to describe
  what it checks, split it.

## What needs tests

- **Every new rule/check** in the scanning engine needs at least: one
  fixture that should trigger it (true positive) and one that
  deliberately looks similar but shouldn't (true negative) — rules with
  no negative-case test tend to accumulate false positives silently.
- **Every parser/adapter** needs tests against malformed/adversarial
  input (truncated files, wrong encoding, deeply nested structures) —
  not just the happy path, since this code processes untrusted input by
  design (see [code-security](../code-security/SKILL.md)).
- **Every bug fix** ships with a regression test that fails before the
  fix and passes after. No fix lands without one.
- **CLI commands**: at least one end-to-end test per command covering
  its primary flag combinations.

## Test hygiene

- Unit tests for core/domain logic: no network, no filesystem, no
  subprocess — pure function in, value out. Mock/stub adapters.
- Integration tests (engine + adapters together) are allowed to touch
  the filesystem via `tmp_path`, but never real network targets — use a
  local fixture server or recorded responses for anything HTTP-shaped.
- Tests must be deterministic: no reliance on wall-clock time, ordering
  of filesystem listings, or network availability. Freeze time / seed
  randomness explicitly where relevant.
- Property-based tests (`hypothesis`) are encouraged for parsing/rule-
  matching logic where the input space is large (e.g. "any valid Python
  source" or "any URL-shaped string") — a fixed example set won't catch
  what fuzzing will.

## Coverage

- Core/domain and engine layers: treat significant coverage drops as a
  signal to add tests, not to lower a threshold. Don't chase 100% by
  padding trivial getters — target the branches that encode real
  decisions (rule matches, severity scoring, boundary conditions).
- CI (once set up) should run the full suite plus lint/type-check on
  every change; a red suite blocks merging, full stop.

## Running tests

- Run the relevant test file(s) directly while iterating
  (`pytest tests/engine/test_scanner.py -k thing`), then the full suite
  before calling a change done.
- A failing test is a bug in the code or a bug in the test — figure out
  which before changing either. Never delete or loosen an assertion just
  to make a test pass without understanding why it failed.
