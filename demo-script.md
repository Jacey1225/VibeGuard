# VibeGuard demo video script — follows the deck, slide by slide

Total runtime target: ~4 min (13 slides + one live-demo interlude after
slide 4). `SAY` = narration, `SHOW` = what's on screen.

---

### Slide 1 — Title
**SHOW:** Title slide, live URL badge.
**SAY:** "This is VibeGuard — a hybrid heuristic and LLM security
scanner that finds vulnerabilities in vibe-coded repos, and commits the
fix, with a human in the loop. Python, FastAPI, Postgres, DeepSeek V3.1
via OpenRouter, GitHub OAuth. It's live right now at
vibeguard-peev.onrender.com."

### Slide 2 — Why this matters
**SHOW:** 42% / 25% stats.
**SAY:** "Forty-two percent of code committed today is AI-written.
Almost none of it gets a security-focused read. A quarter of YC-backed
startups are running on codebases that are ninety-five percent
AI-generated. Vibe coding didn't remove the need for a security review
— it just removed the person who used to do it. So we built this for
that person: paste a repo URL or a snippet, no local setup. Findings
come back in plain English, not a CVE number to go look up. One click
ships the fix, reviewed, straight to GitHub."

### Slide 3 — The problem
**SHOW:** Hardcoded credentials / unsanitized SQL / missing auth checks.
**SAY:** "These are the bugs that never show up in a demo, but sit in
the repo the whole time. And existing scanners either drown you in
false positives, or cost more per scan than a hackathon budget allows."

### Slide 4 — What it does
**SHOW:** Three-stage pipeline card.
**SAY:** "So: three stages. Intake — a repo URL or a pasted snippet.
Scan — local heuristics check every file against ten OWASP-aligned
categories, only matches escalate to an LLM. Remediate — it proposes a
fix, you review the diff, approval pushes it straight to the repo's
default branch. Let me actually show you."

---

### 🎥 LIVE DEMO INTERLUDE (~45–60 sec)
**SHOW:** Switch to the live site / terminal.
**DEMO:** Paste a snippet with an obvious SQL injection — an f-string
built straight into `.execute()`. Submit it, let it scan, show the
finding come back.
**SAY (while it scans):** "That's the fast path — no GitHub needed.
The other pipeline takes a real repo URL, runs the same scan engine,
then keeps going: generate a fix, review the diff, approve, and it's a
real commit on GitHub."
**DEMO:** Cut to a pre-run repo scan → `remediate` → show a `diff_text`
→ `approve` → flip to GitHub and show the commit that just landed.
**SAY:** "One scan, one diff review, one real commit."

---

### Slide 5 — Under the hood (flow diagrams)
**SHOW:** Auth-gate diagram + intake/scan diagram.
**SAY:** "We mapped every one of these flows before writing a line of
code. Auth gates every write. Intake and scan are two entry points —
repo or snippet — but they share one downstream pipeline from there."

### Slide 6 — Under the hood (remediate/decision)
**SHOW:** Remediate → decision flow diagram.
**SAY:** "Remediation only unlocks once a repo's already been scanned.
One proposal per findings-bearing file, and every decision — approve or
reject — is explicit. Push failures on a stale file or a permissions
issue are retryable, not a dead end."

### Slide 7 — Cost-aware scanning
**SHOW:** Every file → matched files → LLM-confirmed findings funnel.
**SAY:** "Token cost scales with signal, not repo size. Heuristics run
over every file at near-zero cost — only real signal ever reaches an
LLM call."

### Slide 8 — Stack
**SHOW:** Stack grid.
**SAY:** "FastAPI and Python 3.12 for the API, Postgres with Alembic
migrations for persistence, DeepSeek V3.1 via OpenRouter for
confirmation and remediation, GitHub OAuth with tokens encrypted at
rest for the push flow. Ports-and-adapters architecture underneath,
pytest and mypy keeping it honest, and a full docs site alongside the
code."

### Slide 9 — The API
**SHOW:** Five-endpoint list.
**SAY:** "The whole repo flow, in five calls: register, scan, pull
findings, generate a remediation, approve it."

### Slide 10 — Challenges
**SHOW:** Without-a-gate / what-we-built-instead cards.
**SAY:** "The remediation push was the hardest part to get right —
writing to someone's default branch is genuinely dangerous. Without a
review gate, that's an automated agent silently rewriting a stranger's
repo with no chance to catch a bad diff. So the diff review at approval
time isn't a nice-to-have — the design makes it unavoidable. Either
build a real gate, or don't ship the push feature at all."

### Slide 11 — Proud of / learned
**SHOW:** Accomplishments / lessons cards.
**SAY:** "What we're proud of: a real end-to-end pipeline, URL in,
reviewed fix committed out. Cost-aware scanning. Tests that spin up
their own throwaway Postgres. A real docs site, not an afterthought.
What we learned: hybrid pipelines beat pure-LLM ones on cost and
precision when you can write a cheap filter for the first pass — and
any tool that writes to a user's repo has to treat approval as a
first-class feature, not a confirmation dialog bolted on at the end."

### Slide 12 — What's next
**SHOW:** Six-item roadmap.
**SAY:** "Next: open a PR instead of pushing straight to default, so
changes go through CI. Support private repos through the OAuth flow we
already have. Broaden past the current ten categories. A background job
queue so a big repo doesn't block the request. IDE integrations. And a
guided, no-CLI flow so this isn't just for developers."

### Slide 13 — Closing
**SHOW:** Tagline + CTA.
**SAY:** "Vibe-code fast. Ship it safe. Try it now at
vibeguard-peev.onrender.com."
