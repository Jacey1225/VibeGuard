---
name: vuln-scan
description: Static, OWASP-style vulnerability review of web application source code. Use when the user asks to scan, audit, or review a codebase for security vulnerabilities, or wants a structured pass over source files for injection, auth, XSS, secrets, and similar issues.
user-invocable: true
---

# /vuln-scan — Web App Source Code Vulnerability Scan

A structured, language-agnostic static review of a codebase. This is a
defensive review skill: it finds and reports issues, it does not exploit
them. For proof-of-concept exploitation against a running target, use
[ctf-pentest](../ctf-pentest/SKILL.md) instead (and only within an
authorized scope).

Arguments passed: `$ARGUMENTS` — optionally a path or glob to scope the
scan (e.g. `src/api`). If empty, scan the whole repo, but confirm the
project root with the user first if it's ambiguous.

## Ground rules

- This is read-only analysis. Never modify application code as part of a
  scan unless the user separately asks you to fix something you found.
- Report findings; don't fabricate them. Every finding must cite a real
  file and line. If you're not sure something is exploitable, say so and
  mark it as needing manual verification rather than asserting severity.
- Prefer grep/Explore-style search over reading every file blind — target
  the categories below with keyword and pattern searches, then read the
  surrounding code for confirmed hits.

## Scope the scan

1. Identify the language(s)/framework(s) in play (check manifest files:
   `package.json`, `requirements.txt`/`pyproject.toml`, `go.mod`,
   `pom.xml`/`build.gradle`, `Gemfile`, `Cargo.toml`, composer.json, etc.).
2. Identify entry points: HTTP routes/controllers, RPC handlers, message
   queue consumers, CLI argument parsing, file upload handlers.
3. Note anything already flagged — existing `# nosec`, `// TODO security`,
   linter suppressions, or a SECURITY.md — as context, not as license to
   skip that code.

## Checklist (OWASP Top 10-aligned)

Work through each category against the scoped code. Skip a category
explicitly (and say why) if it plainly doesn't apply (e.g. no DB present).

1. **Injection** — SQL/NoSQL/OS command/LDAP injection. Look for string
   concatenation or f-strings/template interpolation building queries or
   shell commands from user input. Flag anything not using parameterized
   queries, prepared statements, or an ORM's safe query builder.
2. **Broken authentication & session management** — password storage
   (must be salted+hashed with bcrypt/argon2/scrypt, never plain/MD5/
   SHA1), session token generation (must be cryptographically random),
   missing/weak MFA paths, session fixation, tokens in URLs.
3. **Broken access control** — missing authorization checks on
   routes/handlers (authN without authZ), IDOR (object IDs taken from
   user input without an ownership check), path traversal on file access
   (`../` not sanitized, unsanitized filenames used in filesystem calls).
4. **Cryptographic failures** — hardcoded secrets/keys/credentials in
   source (grep for `api[_-]?key`, `secret`, `password`, `token` literals
   and high-entropy strings), weak algorithms (DES, RC4, MD5/SHA1 for
   security purposes), missing TLS verification (`verify=False`,
   `NODE_TLS_REJECT_UNAUTHORIZED=0`, insecure `SSLContext`), predictable
   IVs/nonces.
5. **XXE / insecure deserialization** — XML parsers with external entity
   resolution enabled, `pickle`/`yaml.load` (unsafe)/`unserialize`/Java
   native deserialization on untrusted input, insecure use of `eval`/
   `exec`/`Function()` constructors.
6. **Security misconfiguration** — debug mode enabled in what looks like
   production config, permissive CORS (`*` with credentials), verbose
   error messages/stack traces returned to clients, default credentials,
   directory listing enabled, missing security headers (CSP, HSTS,
   X-Frame-Options) in the app's HTTP layer.
7. **XSS** — unescaped user input rendered into HTML/JS/attributes,
   `dangerouslySetInnerHTML`/`innerHTML`/`v-html`/`|safe` filters/
   `Markup()` used on untrusted data, missing output encoding in
   templates.
8. **Insecure deserialization / SSRF** — server-side requests built from
   user-supplied URLs/hosts without allowlisting, webhook or "fetch this
   URL" features that can reach internal network ranges.
9. **Vulnerable/outdated dependencies** — check lockfiles for known-bad
   versions if a scanner is available (`npm audit`, `pip-audit`,
   `osv-scanner`, `govulncheck`); otherwise flag obviously stale majors
   and note that a dedicated SCA tool should confirm.
10. **Insufficient logging & monitoring** — auth failures, access-control
    failures, and input-validation failures that aren't logged at all;
    conversely, sensitive data (passwords, tokens, PII) being logged in
    plaintext.

## Reporting

For each confirmed or plausible finding, report:

- **File:line** reference
- **Category** (from the checklist above)
- **Severity**: Critical / High / Medium / Low / Info — based on
  exploitability and impact, not just category
- **Description**: what's wrong, in concrete terms
- **Failure scenario**: a specific input/actor that triggers it
- **Remediation**: the concrete fix (not "add validation" — say what
  validation)

Order findings most-severe first. If nothing survives scrutiny in a
category, don't pad the report — omit it or say "no issues found."

If the `ReportFindings` tool is available in this session and the user's
workflow expects typed findings output, use it instead of a prose report.
