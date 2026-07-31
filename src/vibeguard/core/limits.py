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
