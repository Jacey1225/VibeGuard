"""Directory names pruned from a cloned repository's file walk."""

EXCLUDED_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        "dist",
        "build",
        ".idea",
        ".vscode",
    }
)


def is_excluded_directory(name: str) -> bool:
    """Return whether a directory name should be pruned from the walk."""
    return name in EXCLUDED_DIR_NAMES
