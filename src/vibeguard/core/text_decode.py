"""Decoding raw file bytes into storable text."""


def decode_file_text(raw: bytes) -> str:
    """Decode raw file bytes as UTF-8, replacing undecodable bytes.

    Callers are expected to have already excluded binary content via
    `looks_binary` (see `file_filter.py`); this replaces rather than
    raises so a rare non-UTF-8-but-not-binary-looking file still stores
    something rather than aborting the whole ingest.
    """
    return raw.decode("utf-8", errors="replace")
