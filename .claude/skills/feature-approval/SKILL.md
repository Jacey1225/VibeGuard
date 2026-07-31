---
name: feature-approval
description: Mandatory plan-and-confirm gate before implementing any new feature in VibeGuard, and the entry point that pulls up every other mandatory project skill for that feature. Consult before writing code for a new rule/check, CLI command, integration, or any capability that doesn't exist yet. Applies for the entire life of the project — no silent scope creep.
user-invocable: true
---

# Feature Approval — Plan-and-Confirm Gate

TRIGGER: before writing any code that adds a **new feature** — a new
scan rule/check, a new CLI command, a new integration/adapter, a new
output format, or any capability that doesn't exist yet. Does not apply
to bug fixes, refactors with no behavior change, or work whose exact
scope the user already specified in the same message (e.g. "add a
`--json` flag that does exactly X").

## The gate

0. **Pull up every mandatory skill, explicitly, before drafting the
   plan.** Call the `Skill` tool for each of `architecture`,
   `code-security`, `testing-standards`, `documentation-standards`, and
   `search-sort-efficiency` — and `github-sync-check` if this task
   starts a new coding session — for this feature request specifically.
   Don't rely on having read them earlier in the conversation or on
   memory of their contents; invoke them fresh so the plan is checked
   against their current text. This step is what makes steps 2-4 below
   real instead of a recollection-based approximation of them.
1. **State scope before coding**: what the feature does, and — just as
   important — what it explicitly does not do. Vague scope is how small
   features grow into unreviewed ones.
2. **Name the affected layers**, per [architecture](../architecture/SKILL.md):
   which of core/engine/adapters/cli this touches, and whether it
   introduces a new module or a new dependency.
3. **Flag anything that touches**
   [code-security](../code-security/SKILL.md) surfaces (new subprocess
   call, new network target, new deserialization) or adds a dependency —
   call these out explicitly in the plan so they get scrutiny before,
   not after, the code exists.
4. **Note the test plan**: what [testing-standards](../testing-standards/SKILL.md)
   requires for this feature (new fixtures, true/false-positive cases,
   regression coverage) — sketched before coding, not discovered after.
5. **Note the data-shape plan**: whether
   [search-sort-efficiency](../search-sort-efficiency/SKILL.md) applies
   — any lookups/sorts this feature introduces over findings, rules, or
   files, and which data structure/algorithm choice covers them.
6. **Note what needs documenting**, per
   [documentation-standards](../documentation-standards/SKILL.md): which
   new docstrings, README updates, rule-catalog entries, or changelog
   lines this feature will need.
7. **Get explicit go-ahead** from the user on the plan before writing
   implementation code. A short plan is enough for a small feature; use
   `EnterPlanMode`/`ExitPlanMode` for anything substantial enough to
   warrant the dedicated plan-review flow.

## What this gate is not

- Not a bureaucratic step for trivial, fully-specified asks — if the
  user has already given exact scope, restate it briefly and proceed
  rather than re-litigating a decision they've made.
- Not a substitute for the other mandatory skills — a plan that skips
  architecture, security, testing, efficiency, or documentation
  consideration isn't a complete plan, it's a shortcut back to scope
  creep. Step 0 exists so that skipping isn't possible by omission.
- Not a one-time project-kickoff step — this applies to the 50th feature
  the same as the 1st.

## If scope drifts mid-implementation

If it becomes clear partway through that the feature is bigger than the
approved plan (new module nobody discussed, a dependency not mentioned,
touching a layer that wasn't in scope), stop and flag the drift to the
user rather than quietly absorbing it into "while I'm here."
