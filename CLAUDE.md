# VibeGuard

A security vulnerability scanning / code-review tool. Python.

## Mandatory development standards

Every change in this repo — for the entire life of the project, not just
early on — must adhere to these six project skills.

- [.claude/skills/architecture/SKILL.md](.claude/skills/architecture/SKILL.md) — file/module layout, layering, naming, single-purpose cascade.
- [.claude/skills/code-security/SKILL.md](.claude/skills/code-security/SKILL.md) — secure coding for VibeGuard's own code (distinct from the findings VibeGuard reports about scanned code).
- [.claude/skills/testing-standards/SKILL.md](.claude/skills/testing-standards/SKILL.md) — what needs tests and how.
- [.claude/skills/documentation-standards/SKILL.md](.claude/skills/documentation-standards/SKILL.md) — docstrings, README, rule catalog, changelog.
- [.claude/skills/feature-approval/SKILL.md](.claude/skills/feature-approval/SKILL.md) — plan-and-confirm gate before implementing any new feature (not bugfixes/refactors).
- [.claude/skills/search-sort-efficiency/SKILL.md](.claude/skills/search-sort-efficiency/SKILL.md) — data structure/algorithm choices for any search, lookup, or sort over findings/rules/files.

**Every feature request must go through `feature-approval` first** —
not just be silently informed by it. `feature-approval`'s step 0 is an
explicit instruction to call the `Skill` tool for each of the other five
standards above (plus `github-sync-check` when relevant) before drafting
a plan, so this isn't left to proactive judgment or memory of a skill
read earlier in the conversation. This is the mechanism that guarantees
every one of these gets pulled up for every feature request, not just
the ones that happen to look relevant at a glance.

These six apply together on any non-trivial change: scope the feature
(feature-approval, which pulls up the rest) → place it correctly
(architecture) → keep it safe (code-security) → make it efficient
(search-sort-efficiency) → cover it (testing-standards) → document it
(documentation-standards).

## Git workflow

- [.claude/skills/github-sync-check/SKILL.md](.claude/skills/github-sync-check/SKILL.md) — mandatory before starting any coding task: fetch and check for incoming collaborator commits that conflict with the planned work, report them, and let the user decide how to proceed. Read-only — never pulls, merges, or pushes on its own.

## Other project skills

- [.claude/skills/vuln-scan/SKILL.md](.claude/skills/vuln-scan/SKILL.md) — OWASP-style static review of a *target* codebase (a user-facing capability of the tool, and also usable on VibeGuard's own code on request).
- [.claude/skills/ctf-pentest/SKILL.md](.claude/skills/ctf-pentest/SKILL.md) — CTF web-challenge and authorized-pentest workflow, gated on authorization.
