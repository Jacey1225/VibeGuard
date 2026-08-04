# VibeGuard frontend — Vibecheck

A React + TypeScript + Vite implementation of **Vibecheck**, the
product-facing UI for VibeGuard: paste code (or connect a GitHub
project), watch it get checked, decide which findings to fix, watch
the fixes apply, and review the diff before sending it on.

## Status: UI-only simulation

This is a pixel-faithful port of a Claude Design prototype. It runs
entirely on **canned fixture data and simulated timers** — it does not
call VibeGuard's real API (`src/vibeguard/api`). Specifically:

- The composer's "paste code" path has no backing endpoint yet — the
  real API is repository-URL-based only (`POST /repositories`).
- The "scanning" screen's animated per-file progress is simulated;
  the real `POST /repositories/{id}/scan` blocks for the whole scan
  with no progress events.
- The findings, their code snippets, and the fixes shown are fixed
  demo data (`src/data/fixtures.ts`), not real findings.
- "Send these changes" simulates a single batch action; the real API
  approves remediations one at a time (`POST /remediations/{id}/approve`),
  each pushed individually — there's no batch-PR endpoint.

Wiring this UI to the real backend is a separate, explicitly-scoped
feature, not something this change does implicitly.

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
    screens/               one component per flow screen (0-5)
    composer/ findings/ fixing/ diff/   screen-scoped subcomponents
    icons.tsx, Header.tsx, StepNav.tsx  shared chrome
  styles/                  design tokens + global CSS (fonts, keyframes)
```
