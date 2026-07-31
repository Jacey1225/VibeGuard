---
name: github-sync-check
description: Mandatory pre-change check for incoming collaborator commits on GitHub. Before starting a new coding task, fetch the remote and compare against the current branch to surface conflicts before editing begins, not after. Applies for the entire life of the project.
user-invocable: true
---

# GitHub Sync Check — Pre-Change Collaborator Conflict Detection

TRIGGER: before starting a new coding task in this repo — at the
beginning of a working session, or before beginning a task that will
touch code. This is a read-only check: it reports and stops. You never
pull, merge, rebase, or push on your own — the user handles all pushes,
and decides how to resolve anything found.

## What this checks

Branch-level divergence only: whether a collaborator has pushed commits
to the remote tracking branch since the local branch last synced. This
does not scan open pull requests — just the current branch against its
remote counterpart.

## Procedure

1. Confirm this is a git repo with a configured remote
   (`git rev-parse --is-inside-work-tree`, `git remote -v`). If either
   check fails, say so and skip the rest — nothing to check yet.
2. `git fetch` the remote. Read-only, safe to run without asking.
3. Compare the local branch to its upstream: `git status -sb` and
   `git log HEAD..origin/<branch> --oneline` to list any incoming
   commits not yet in the local branch.
4. If nothing is incoming, say so in one line and proceed with the
   requested work — don't belabor a clean check.
5. If commits are incoming:
   - List them: short SHA, author, subject.
   - Run `git diff HEAD...origin/<branch> --stat` to see which files
     they touch.
   - Compare that file list against the files the upcoming task is
     about to touch. Call out the overlap explicitly — that's the real
     conflict risk, not just "commits exist upstream."
   - If there are uncommitted local changes (`git status`), check
     whether those specific files also appear in the incoming set —
     that's a near-certain merge conflict, not just a risk, and should
     be flagged more urgently than a plain overlap.
6. **Report and stop.** Present: the incoming commits, which files
   overlap with the planned work (if any), and whether local
   uncommitted changes are directly in conflict. Then let the user
   choose how to proceed — pull/sync first, work on different files,
   proceed anyway and resolve later, or wait. Don't pick for them and
   don't take any resolving action yourself.

## What this skill does not do

- Never runs `git pull`, `merge`, `rebase`, `reset`, or any other
  state-changing git command on its own — only read-only checks
  (`fetch`, `status`, `log`, `diff`).
- Never pushes. Pushing is the user's action, always.
- Doesn't scan open pull requests via `gh pr list` or similar — that's
  a broader check than what's scoped here. If that's wanted later, it
  belongs in a separate step, not folded silently into this one.
- Isn't a per-edit gate. Running `git fetch` before every single `Edit`
  call would be noisy for no benefit — run this once at the start of a
  task or session, not on every tool call within it.
