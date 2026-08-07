# VibeGuard frontend — Vibecheck

A React + TypeScript + Vite implementation of **Vibecheck**, the
product-facing UI for VibeGuard: paste code (or connect a GitHub
project), watch it get checked, decide which findings to fix, watch
the fixes apply, and review the diff before sending it on.

## Status: three parallel paths — real repository findings, real GitHub-free snippet findings, and fixture demo

This started as a pixel-faithful port of a Claude Design prototype
running entirely on canned fixture data and simulated timers. That demo
path still exists unchanged, alongside two real, API-backed paths:

- Connecting a real GitHub repository (`POST /repositories`) takes over
  the whole flow with a **real, API-backed** path:
  - The "scanning" screen's animated per-file progress is simulated on
    top of a real, blocking `POST /repositories/{id}/scan` call —
    there's no server-sent progress, so the animation just estimates
    duration.
  - Once a real scan produces findings, screens 2-5 switch to the
    real-data path (`RealFindingsPanel`, `RealRemediationScreen`,
    `RealRemediationReviewScreen`, `RealRemediationDoneScreen`): the
    code preview on each finding card comes from the backend's
    already-cloned scan copy (`GET /repositories/{id}/files/preview`,
    never a live, unauthenticated call to `api.github.com`), "Fix N
    now" calls `POST /repositories/{id}/remediate`, and each proposed
    fix is individually approved or rejected
    (`POST /remediations/{id}/approve` or `/reject`) — there's no
    batch-PR endpoint, and approval pushes a direct commit, not a PR.
  - Remediation routes require a GitHub-OAuth-derived bearer token; the
    app completes that round trip itself (`GET /auth/github/login` →
    `/auth/github/callback` → `#session_token=...` read from the URL
    fragment on return, see `useVibecheckFlow`'s `signInWithGithub` /
    `startRemediation`) rather than requiring a separate sign-in step.
- The composer's "+" menu also has a **"Scan pasted code — no GitHub
  needed"** option — a real, API-backed scan of pasted plain-text code
  with zero GitHub interaction anywhere in the path. Submitting calls
  `POST /snippets` then `POST /snippets/{id}/scan` directly (both
  block until done, so there's no separate scanning screen — success
  jumps straight to screen 2's `SnippetFindingsPanel`). Each finding
  renders on a `SnippetFindingCard`, which slices code context
  client-side from the snippet's own submitted text (there's no
  server-side file to preview) and offers a per-finding
  fix-submission control (`SnippetFixControl`,
  `POST`/`GET /snippets/{id}/findings/{finding_id}/fix`) — the user
  pastes their own already-fixed code; it's just recorded, not
  LLM-generated, and nothing gets pushed anywhere. This path's state
  (`snippetId`/`snippetContent`/`snippetFindings`) is fully separate
  from both the repository path (`repoId`/`realFindings`) and the
  fixture demo, and never crosses into repository-only endpoints.
- The fixture demo path (composer paste-code without a connected repo
  or submitted snippet, or `state.findings`) is untouched and still
  runs entirely on `src/data/fixtures.ts` and simulated timers — see
  `FindingsScreen`'s branch on `state.snippetId`, then
  `state.realFindings.length > 0`, for where the three paths split.

## Setup

Requires Node 20+.

```bash
npm install
```

## Running

```bash
npm run dev       # dev server with HMR
npm run build     # typecheck + production build to dist/
npm run preview   # serve the production build locally
```

## Testing

```bash
npm run test        # vitest
npm run typecheck   # tsc --noEmit
npm run lint         # eslint
```

Tests target the extracted state-machine and pure logic (`src/hooks`,
`src/utils`) rather than full-DOM rendering — see
`src/hooks/useVibecheckFlow.test.tsx` and `src/utils/*.test.ts`.

## Structure

```
src/
  App.tsx                 top-level screen switch + shared chrome
  hooks/useVibecheckFlow.ts   the flow's state machine (screens, timers)
  data/fixtures.ts         demo findings/files/scope-items/code snippets
  utils/                   detectLanguage, snippet slicing, severity sort
  components/
    screens/               one component per flow screen (0-5), plus the
                            real-data Real* screens rendered instead of
                            the fixture screen once realFindings is set
    composer/ findings/ fixing/ diff/ remediation/   screen-scoped subcomponents
    icons.tsx, Header.tsx, StepNav.tsx  shared chrome
  styles/                  design tokens + global CSS (fonts, keyframes)
```
