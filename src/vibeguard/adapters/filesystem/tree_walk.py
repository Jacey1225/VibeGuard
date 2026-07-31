"""Walking a cloned repository's file tree, pruning excluded directories."""

import os
from collections.abc import Iterator
from pathlib import Path

from vibeguard.core.excluded_dirs import is_excluded_directory


def walk_clone_tree(clone_root: Path) -> Iterator[Path]:
    """Yield every candidate file under `clone_root`.

    Prunes excluded directories (`.git`, `node_modules`, etc.) before
    descending into them, and skips symlinks entirely — `os.walk`
    already doesn't follow symlinked directories by default, and this
    additionally excludes symlinked regular files from the yielded set.
    """
    for current_dir, dir_names, file_names in os.walk(clone_root):
        dir_names[:] = [name for name in dir_names if not is_excluded_directory(name)]
        for file_name in file_names:
            path = Path(current_dir) / file_name
            if path.is_symlink():
                continue
            yield path
