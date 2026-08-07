"""Pure windowing logic for a finding's file preview: N lines of context around one line.

No I/O here -- the caller (`engine/file_preview.py`) is responsible for
resolving which file's content to pass in.
"""

from __future__ import annotations

from dataclasses import dataclass


class LineOutOfRangeError(RuntimeError):
    """Raised when the requested line number doesn't exist in the given content."""


@dataclass(frozen=True)
class PreviewLine:
    """One 1-indexed line of a file preview."""

    number: int
    text: str


@dataclass(frozen=True)
class FilePreviewWindow:
    """A contiguous slice of a file's lines, centered on `highlight_line`."""

    lines: list[PreviewLine]
    highlight_line: int


def build_preview_window(
    content: str, line_number: int, lines_before: int, lines_after: int
) -> FilePreviewWindow:
    """Build a windowed, 1-indexed preview of `content` centered on `line_number`.

    Args:
        lines_before: how many lines to include before `line_number`,
            clamped at the start of the file.
        lines_after: how many lines to include after `line_number`,
            clamped at the end of the file.

    Raises:
        LineOutOfRangeError: `line_number` is outside `content`'s
            current line count (e.g. the file has changed since the
            finding was produced, or the line was miscomputed).
    """
    all_lines = content.split("\n")
    center_idx = line_number - 1
    if center_idx < 0 or center_idx >= len(all_lines):
        raise LineOutOfRangeError(
            f"line {line_number} is outside the file's current length "
            f"({len(all_lines)} lines)"
        )

    start_idx = max(0, center_idx - lines_before)
    end_idx = min(len(all_lines), center_idx + lines_after + 1)

    lines = [
        PreviewLine(number=start_idx + offset + 1, text=text)
        for offset, text in enumerate(all_lines[start_idx:end_idx])
    ]
    return FilePreviewWindow(lines=lines, highlight_line=line_number)
