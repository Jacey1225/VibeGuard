"""Computing a human-reviewable unified diff between two file versions."""

import difflib


def compute_unified_diff(original: str, proposed: str, relative_path: str) -> str:
    """Return a unified diff of `original` -> `proposed` for one file.

    Empty string if the two are identical (a no-op fix).
    """
    diff_lines = difflib.unified_diff(
        original.splitlines(keepends=True),
        proposed.splitlines(keepends=True),
        fromfile=f"a/{relative_path}",
        tofile=f"b/{relative_path}",
    )
    return "".join(diff_lines)
