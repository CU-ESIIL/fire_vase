"""Utilities for rendering the cube viewer safely inside notebooks."""

from __future__ import annotations

import errno
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from IPython.display import IFrame


def _write_cube_html(html: str, prefix: str = "cube_viewer") -> str:
    """Write a standalone cube viewer HTML file to the working directory."""

    viewer_id = uuid.uuid4().hex
    filename = f"{prefix}_{viewer_id}.html"
    path = Path(filename)
    try:
        path.write_text(html, encoding="utf-8")
        return filename
    except OSError as exc:
        if exc.errno not in {errno.EACCES, errno.EROFS}:
            raise
        fallback = Path(tempfile.gettempdir()) / filename
        fallback.write_text(html, encoding="utf-8")
        return str(fallback)


def show_cube_viewer(html: str, *, width: int = 850, height: int = 850, prefix: Optional[str] = None) -> IFrame:
    """Return an IFrame pointing at a self-contained cube viewer file.

    Jupyter will happily render ``<iframe>`` blocks while sanitizing inline
    ``<script>`` tags. Writing the viewer to disk and loading it in an IFrame
    keeps the JavaScript intact without requiring notebook trust.
    """

    html_prefix = prefix or "cube_viewer"
    path = _write_cube_html(html, prefix=html_prefix)
    iframe = IFrame(path, width=width, height=height)
    iframe.cube_viewer_path = path  # type: ignore[attr-defined]
    return iframe


__all__ = ["show_cube_viewer", "_write_cube_html"]
