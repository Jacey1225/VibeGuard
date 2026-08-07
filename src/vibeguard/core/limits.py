"""Default resource-limit constants for repository intake.

These bound every operation that runs over attacker-controlled input (a
public GitHub repository can be arbitrarily large or malicious). See
code-security's "Resource limits" section — these are not tunable away,
only overridable via Settings for legitimate operational reasons.
"""

DEFAULT_MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024
DEFAULT_MAX_TOTAL_SIZE_BYTES = 200 * 1024 * 1024
DEFAULT_MAX_FILE_COUNT = 20_000
DEFAULT_CLONE_TIMEOUT_SECONDS = 60
DEFAULT_GITHUB_API_TIMEOUT_SECONDS = 5.0

# GitHub's reported repo `size` (KB) is a conservative, whole-history
# estimate that can overstate the size of a `--depth 1` clone. Allow
# slack before rejecting pre-clone so we don't reject repos that would
# actually fit.
DEFAULT_PRECHECK_SIZE_FUDGE_FACTOR = 1.5

# Reading admitted files' contents during intake is I/O-bound (disk
# reads); parallelized across this many worker threads.
DEFAULT_INGEST_THREAD_POOL_SIZE = 8

# Vulnerability scan engine (LLM calls are I/O-bound network requests).
DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS = 30.0
DEFAULT_LLM_MAX_TOKENS = 1024
DEFAULT_MAX_LLM_CALLS_PER_SCAN = 150
DEFAULT_MAX_CONCURRENT_LLM_CALLS = 6

# Auth: sessions and the OAuth CSRF-protection cookie.
DEFAULT_SESSION_TTL_HOURS = 24
DEFAULT_OAUTH_STATE_COOKIE_TTL_SECONDS = 600

# Remediation engine (a full-file rewrite costs more tokens than a
# findings-only confirmation, so a higher per-call ceiling than the
# scan engine's).
DEFAULT_REMEDIATION_LLM_MAX_TOKENS = 4096
DEFAULT_MAX_LLM_CALLS_PER_REMEDIATION = 50
DEFAULT_MAX_CONCURRENT_REMEDIATION_LLM_CALLS = 6

# File preview (a finding's code-location card): how many lines of
# context surround the reported line on each side.
DEFAULT_FILE_PREVIEW_LINES_BEFORE = 5
DEFAULT_FILE_PREVIEW_LINES_AFTER = 5
