---
name: documentation-standards
description: Mandatory documentation standards for VibeGuard (docstrings, README, rule documentation, changelog). Consult whenever adding a public function/class/module, a new scan rule, or a user-facing change. Applies for the entire life of the project.
user-invocable: true
---

# Documentation Standards

TRIGGER: read whenever adding a public function/class/module, a new
scan rule/check, a CLI command, or any user-facing behavior change.

This governs *documentation artifacts* (docstrings, README, rule
descriptions, changelog) — it does not relax the project's default of
no inline comments. Inline comments still only belong where the WHY
isn't obvious from the code itself (a non-obvious constraint, a
workaround, a subtle invariant); well-named code shouldn't need them.

## Docstrings

- Every **public** function, class, and module gets a docstring. Private
  helpers (`_leading_underscore`) only need one if their behavior isn't
  obvious from the name and signature.
- Format: one-line summary, blank line, then `Args`/`Returns`/`Raises`
  sections only when they add information beyond the type hints — don't
  restate `x: int` as "x: an integer."
- Type hints are the primary documentation for shapes; docstrings
  document *behavior and intent*, not types already visible in the
  signature.
- A scan rule's docstring must state: what pattern it detects, a
  realistic false-positive scenario if one exists, and the remediation
  guidance shown to the end user for that finding — this triples as the
  spec, the test-writing guide, and the user-facing text.

## README

- Kept current with: what VibeGuard does, install/setup, how to run a
  scan, how to add a new rule. If a change makes any of these stale,
  update the README in the same change — not as a follow-up.

## Rule/check catalog

- Once there's more than a handful of rules, maintain a single catalog
  (doc or generated from rule metadata) listing every check, its ID,
  severity default, and what it detects — so rules don't end up
  documented only in their own docstring with no discoverable index.

## Changelog

- User-facing changes (new rules, new CLI flags, behavior changes,
  bug fixes affecting output) get a `CHANGELOG.md` entry. Internal
  refactors with no observable effect don't need one.

## What NOT to document

- Don't write docstrings that just restate the function name in prose.
- Don't create planning/design docs in the repo for routine work — that
  belongs in the [feature-approval](../feature-approval/SKILL.md) plan
  shared with the user in-conversation, not as a committed file, unless
  the user asks for a persisted design doc.
- Don't let generated/derived docs (e.g. an auto-generated rule catalog)
  drift out of sync with a hand-maintained copy — generate it, don't
  duplicate it by hand.
