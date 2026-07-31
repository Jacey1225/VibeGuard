"""Cheap pre-clone size circuit breaker.

GitHub's reported repository `size` (KB) is a conservative, whole-history
estimate that can overstate what a `--depth 1` clone would actually
occupy, so a fudge factor is applied before rejecting a submission this
cheaply, without ever having attempted the clone.
"""


def exceeds_precheck_size_budget(size_kb: int, max_total_bytes: int, fudge_factor: float) -> bool:
    """Return whether GitHub's reported size clears the pre-clone budget."""
    reported_bytes = size_kb * 1024
    return reported_bytes > max_total_bytes * fudge_factor
