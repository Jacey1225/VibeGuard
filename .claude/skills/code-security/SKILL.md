---
name: code-security
description: Mandatory secure-coding rules for VibeGuard's own codebase (as opposed to code VibeGuard scans). Consult whenever writing code that handles subprocess calls, file paths, network targets, secrets, or any externally-sourced/untrusted data. Applies for the entire life of the project.
user-invocable: true
---

# Code Security — Secure Coding Standards for VibeGuard Itself

This is about the security of the code we write for VibeGuard, not the
findings VibeGuard produces about other codebases (that's
[vuln-scan](../vuln-scan/SKILL.md)). VibeGuard is a security tool that
will parse untrusted source files, run external scanners, and (in
[ctf-pentest](../ctf-pentest/SKILL.md) mode) send requests to real
targets — which makes its own attack surface unusually sensitive: a bug
here can turn a security tool into the vulnerability.

TRIGGER: read before writing/reviewing any code that: shells out to a
subprocess, builds a filesystem path from input, makes an outbound
network request, handles secrets/credentials, or deserializes data from
a scanned target or file.

## Untrusted input boundaries

Treat as untrusted, always: file contents being scanned, filenames/paths
from a scanned tree, HTTP responses from a pentest/CTF target, anything
read from a config file that isn't VibeGuard's own.

- **Subprocess calls**: always pass args as a list (`subprocess.run([...],
  shell=False)`), never build a shell string via concatenation/f-string.
  Never set `shell=True` with any value derived from scanned/target input.
- **Path handling**: resolve and validate that any path derived from
  scanned input stays within the intended scan root
  (`Path.resolve()` + containment check) before opening/reading it —
  scanned archives or symlinks can otherwise escape the intended
  directory (zip-slip / symlink traversal).
- **Deserialization**: never `pickle.load`/`yaml.load` (unsafe) on data
  from a scanned target or file. Use `yaml.safe_load`, `json`, or a
  schema-validated parser.
- **No `eval`/`exec`/dynamic `Function`-style construction** on anything
  derived from scanned or target input, ever — including "just for
  convenience" in the scanning engine itself.
- **Outbound requests in pentest mode**: always use the vetted HTTP
  client wrapper (once one exists) rather than ad hoc calls, so
  timeouts, redirect limits, and scope-allowlist checks stay centralized
  in one place instead of being re-implemented (or forgotten) per call
  site.

## Secrets & credentials

- No hardcoded API keys, tokens, or credentials in source, tests, or
  fixtures — including "obviously fake-looking" placeholders that could
  be mistaken for real ones later. Use environment variables or a
  secrets manager.
- If a scan or test target legitimately requires a credential (e.g.
  testing an authenticated endpoint), load it from env/config that's
  gitignored, never commit it.
- If VibeGuard's own scanning logic *finds* a secret in target code,
  never echo the full secret value in logs or default output — redact to
  a prefix/suffix and let full-value display be an explicit opt-in.

## Dependencies

- Every new dependency goes through `pyproject.toml` with a pinned
  version, per [architecture](../architecture/SKILL.md).
- Prefer well-maintained, widely-used libraries for anything
  security-relevant (crypto, parsing untrusted formats). Don't hand-roll
  parsing for a format that has a hardened library already.
- Run `pip-audit` (or equivalent) before adding a dependency with a
  history of CVEs, and periodically against the lockfile as a whole.

## Resource limits

- Any operation over scanned/target input needs a bound: timeout on
  subprocess/network calls, recursion/size limits on file tree walks
  (guards against zip bombs, deeply nested directories, symlink loops).
  Don't rely on the target being well-behaved.

## Logging

- Never log full request/response bodies from a pentest target, secrets
  discovered during a scan, or credentials — even at debug level.
- Do log enough to reconstruct what VibeGuard did (which check ran,
  which file/endpoint, outcome) without leaking sensitive payloads.
