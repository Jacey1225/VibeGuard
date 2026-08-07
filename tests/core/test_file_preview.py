"""Tests for the pure file-preview windowing logic (no I/O, no DB)."""

import pytest

from vibeguard.core.file_preview import LineOutOfRangeError, build_preview_window


def _content(n_lines: int) -> str:
    return "\n".join(f"line{i}" for i in range(1, n_lines + 1))


def test_build_preview_window_centers_on_requested_line():
    window = build_preview_window(_content(20), line_number=10, lines_before=5, lines_after=5)

    assert window.highlight_line == 10
    assert [line.number for line in window.lines] == list(range(5, 16))
    assert [line.text for line in window.lines] == [f"line{i}" for i in range(5, 16)]


def test_build_preview_window_clamps_at_start_of_file():
    window = build_preview_window(_content(20), line_number=2, lines_before=5, lines_after=5)

    # Can't go before line 1 -- window starts at 1, not a negative offset.
    assert window.lines[0].number == 1
    assert window.highlight_line == 2


def test_build_preview_window_clamps_at_end_of_file():
    window = build_preview_window(_content(20), line_number=19, lines_before=5, lines_after=5)

    # Can't go past the last line -- window ends at 20, not beyond it.
    assert window.lines[-1].number == 20
    assert window.highlight_line == 19


def test_build_preview_window_single_line_file():
    window = build_preview_window("only line", line_number=1, lines_before=5, lines_after=5)

    assert [line.number for line in window.lines] == [1]
    assert window.lines[0].text == "only line"


@pytest.mark.parametrize("line_number", [0, -1])
def test_build_preview_window_rejects_non_positive_line(line_number: int):
    with pytest.raises(LineOutOfRangeError):
        build_preview_window(_content(5), line_number=line_number, lines_before=5, lines_after=5)


def test_build_preview_window_rejects_line_past_end_of_file():
    with pytest.raises(LineOutOfRangeError):
        build_preview_window(_content(5), line_number=6, lines_before=5, lines_after=5)


def test_build_preview_window_error_message_reports_actual_file_length():
    with pytest.raises(LineOutOfRangeError, match="5 lines"):
        build_preview_window(_content(5), line_number=100, lines_before=5, lines_after=5)
