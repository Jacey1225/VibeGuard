"""Response body for the file preview endpoint."""

from pydantic import BaseModel


class PreviewLineResponse(BaseModel):
    """One 1-indexed line of a file preview."""

    number: int
    text: str


class FilePreviewResponse(BaseModel):
    """A windowed, line-numbered preview of a stored file, centered on `highlight_line`."""

    relative_path: str
    lines: list[PreviewLineResponse]
    highlight_line: int
