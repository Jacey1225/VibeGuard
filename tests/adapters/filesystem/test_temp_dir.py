"""Tests for ephemeral clone-directory lifecycle."""

from vibeguard.adapters.filesystem.temp_dir import create_ephemeral_clone_dir, remove_clone_dir


def test_create_ephemeral_clone_dir_creates_an_empty_directory():
    path = create_ephemeral_clone_dir()
    try:
        assert path.exists()
        assert path.is_dir()
        assert list(path.iterdir()) == []
    finally:
        remove_clone_dir(path)


def test_remove_clone_dir_removes_directory_and_contents():
    path = create_ephemeral_clone_dir()
    (path / "file.txt").write_text("x")
    remove_clone_dir(path)
    assert not path.exists()


def test_remove_clone_dir_is_idempotent_on_already_removed_path():
    path = create_ephemeral_clone_dir()
    remove_clone_dir(path)
    remove_clone_dir(path)  # should not raise
