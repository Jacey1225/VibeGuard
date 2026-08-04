import type { CodeSnippet, FileFixture, ScopeItemDef, Severity, SeverityInfo } from "../types";

/**
 * Demo fixture data for the Vibecheck flow. Every screen in this UI runs
 * against this canned data and simulated timers rather than VibeGuard's
 * real scan/remediation API — see frontend/README.md for why, and what
 * wiring it up for real would involve.
 */

export const SEVERITY: Record<Severity, SeverityInfo> = {
  high: { label: "Serious", color: "#FF6B5A", soft: "#FF8B7C", tint: "rgba(255,107,90,0.13)" },
  medium: { label: "Worth fixing", color: "#F5B544", soft: "#FFCE74", tint: "rgba(245,181,68,0.12)" },
  low: { label: "Minor", color: "#9AA0A6", soft: "#C3C8CC", tint: "rgba(255,255,255,0.07)" },
};

export const PLACEHOLDERS: readonly string[] = [
  "Paste the file you are worried about…",
  "Drop in your login or signup code…",
  "Paste your database setup…",
  "Anything from your AI coding tool works here…",
];

export const FILES: readonly FileFixture[] = [
  {
    name: "src/lib/db.js",
    short: "db.js",
    lang: "JavaScript",
    findingId: 1,
    start: 0,
    end: 3,
    rows: [92, 64, 78, 48, 84],
  },
  {
    name: "src/api/auth/login.js",
    short: "login.js",
    lang: "JavaScript",
    findingId: 2,
    start: 1,
    end: 4,
    rows: [70, 88, 52, 76, 60],
  },
  {
    name: "src/api/user/profile.js",
    short: "profile.js",
    lang: "JavaScript",
    findingId: 3,
    start: 2,
    end: 5,
    rows: [84, 56, 72, 90, 46],
  },
  {
    name: "src/config/cors.js",
    short: "cors.js",
    lang: "Config",
    findingId: null,
    start: 3,
    end: 6,
    rows: [60, 74, 44, 82, 68],
  },
];

export const PIPELINE_TOTAL_TICKS = 7;

export const SCAN_MESSAGES: readonly string[] = [
  "Opening your files…",
  "Looking for passwords and keys left in the code…",
  "Checking who can log in, and how many tries they get…",
  "Checking what your database lets people read and write…",
  "Comparing everything against common safety standards…",
  "Almost done…",
];

export const SCOPE_ITEMS: readonly ScopeItemDef[] = [
  {
    key: "secrets",
    label: "Hardcoded secrets & API keys",
    desc: "Secret keys typed straight into the code, where anyone visiting your site could find and reuse them.",
  },
  {
    key: "auth",
    label: "Authentication & access control",
    desc: "How people sign in, and whether someone could reach pages or data meant only for you or your team.",
  },
  {
    key: "db",
    label: "Database permissions",
    desc: "Whether a visitor could read, change, or delete records they should never be able to touch.",
  },
  {
    key: "headers",
    label: "CORS & security headers",
    desc: "Which other websites are allowed to talk to your app and quietly pull information out of it.",
  },
  {
    key: "deps",
    label: "Dependency vulnerabilities",
    desc: "The outside packages your project installs. Old versions often have publicly known ways in.",
  },
  {
    key: "compliance",
    label: "Privacy & compliance basics",
    desc: "How you store personal data, measured against the standards most apps are expected to meet.",
  },
];

export const CODE_SNIPPETS: Readonly<Record<number, CodeSnippet>> = {
  1: {
    file: "src/lib/db.js",
    lines: [
      "import { createClient } from '@supabase/supabase-js'",
      "",
      "const supabase = createClient(",
      "  process.env.SUPABASE_URL,",
      "  'sbp_service_role_51f9a3c2'",
      ")",
      "",
      "export async function getProfile(id) {",
    ],
    startLine: 10,
    flagLine: 14,
    fixedLine: "  process.env.SUPABASE_KEY,",
    fixSummary: "We move the key into a private setting only your server can read.",
    doneSummary: "The key now lives in a private setting on your server, so visitors never see it.",
    working: "Moving the secret key out of your code…",
    achievement: "Your master password is secured",
  },
  2: {
    file: "src/api/auth/login.js",
    lines: [
      "import { Router } from 'express'",
      "import { handleLogin } from './handlers'",
      "",
      "const router = Router()",
      "",
      "router.post('/login', handleLogin)",
      "",
      "export default router",
    ],
    startLine: 1,
    flagLine: 6,
    fixedLine: "router.post('/login', rateLimit({ max: 5 }), handleLogin)",
    fixSummary: "We cap login attempts at 5 every 15 minutes.",
    doneSummary: "Your login page now allows 5 tries every 15 minutes, which stops password-guessing bots.",
    working: "Adding a limit to how often someone can try to log in…",
    achievement: "Password-guessing bots are blocked",
  },
  3: {
    file: "src/api/user/profile.js",
    lines: [
      "export default function handler(req, res) {",
      "  res.setHeader('Allow-Origin', '*')",
      "  res.setHeader('Allow-Credentials', 'true')",
      "",
      "  return res.json(getProfile(req.userId))",
      "}",
    ],
    startLine: 1,
    flagLine: 2,
    fixedLine: "  res.setHeader('Allow-Origin', 'https://app.acme.com')",
    fixSummary: "We limit this to requests coming from your own app.",
    doneSummary: "Only your own app can request this information now, instead of any site on the internet.",
    working: "Locking this request down to your own app…",
    achievement: "Your users’ data is locked to your app",
  },
};

export const EXAMPLE_CODE =
  "const supabase = createClient(\n  process.env.SUPABASE_URL,\n  'sbp_service_role_51f9a3c2'\n)";

export const INITIAL_FINDINGS = [
  {
    id: 1,
    severity: "high" as Severity,
    title: "A master password is visible to everyone",
    plain:
      "The key that unlocks your entire database is sitting in code that every visitor downloads. Anyone who looks could copy it and read, change, or delete all of your data.",
    status: "pending" as const,
  },
  {
    id: 2,
    severity: "medium" as Severity,
    title: "Nothing stops endless login attempts",
    plain:
      "Your login page lets anyone try as many passwords as they want. A bot can guess thousands per minute until one works.",
    status: "pending" as const,
  },
  {
    id: 3,
    severity: "medium" as Severity,
    title: "Any website can request your users’ info",
    plain:
      "Your app answers questions from any site on the internet. A fake site could quietly pull your users’ private details while they are signed in.",
    status: "pending" as const,
  },
];
