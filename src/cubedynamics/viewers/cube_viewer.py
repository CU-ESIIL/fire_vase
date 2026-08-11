from __future__ import annotations

import base64
import io
from importlib import resources
from pathlib import Path
from typing import Tuple

import numpy as np
import xarray as xr
from PIL import Image
from matplotlib import colormaps

from ..deprecations import warn_deprecated
from ..utils.drift_centering import drift_centering_script


def _infer_dims(da: xr.DataArray) -> Tuple[str, str, str]:
    """Infer time, y, x dims for a 3D DataArray.

    The function prefers explicit time-like dimension names, otherwise falls back
    to a heuristic where the longest dimension (greater than 100 elements) is
    treated as time. Remaining dimensions are ordered as (y, x).

    Parameters
    ----------
    da: xr.DataArray
        Input 3D data array.

    Returns
    -------
    tuple[str, str, str]
        The inferred (time_dim, y_dim, x_dim).

    Raises
    ------
    TypeError
        If the input is not an xarray.DataArray.
    ValueError
        If the array is not 3D or dimensions cannot be resolved.
    """

    if not isinstance(da, xr.DataArray):
        raise TypeError("write_cube_viewer expects an xarray.DataArray")

    dims = list(da.dims)
    if len(dims) != 3:
        raise ValueError(
            "write_cube_viewer expects a 3D DataArray; "
            f"found {len(dims)} dims: {dims}"
        )

    time_dim: str | None = None
    for dim in dims:
        if dim.lower() in {"time", "t"}:
            time_dim = dim
            break

    if time_dim is None:
        long_dims = [dim for dim in dims if da.sizes.get(dim, 0) > 100]
        if long_dims:
            time_dim = long_dims[0]
        else:
            time_dim = dims[0]

    spatial_dims = [dim for dim in dims if dim != time_dim]
    if len(spatial_dims) != 2:
        raise ValueError(
            f"Could not infer spatial dimensions from dims={dims}; "
            f"resolved time_dim={time_dim}"
        )

    y_dim, x_dim = spatial_dims[-2], spatial_dims[-1]
    return time_dim, y_dim, x_dim


def _extract_faces(
    da: xr.DataArray, time_dim: str, y_dim: str, x_dim: str
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract cube faces for top (time slice), front (x slice), and side (y slice)."""

    top = da.isel({time_dim: -1}).transpose(y_dim, x_dim).values
    front = da.isel({x_dim: 0}).transpose(time_dim, y_dim).values
    side = da.isel({y_dim: -1}).transpose(time_dim, x_dim).values
    return top, front, side


def _face_to_base64(
    face: np.ndarray, cmap: str, vmin: float, vmax: float
) -> str:
    """Convert a 2D array face to a base64-encoded PNG using a matplotlib colormap."""

    safe_vmax = vmax if vmax != vmin else vmin + 1.0
    scaled = (np.nan_to_num(face, nan=vmin) - vmin) / (safe_vmax - vmin)
    scaled = np.clip(scaled, 0.0, 1.0)
    rgba = (colormaps.get_cmap(cmap)(scaled) * 255).astype(np.uint8)

    image = Image.fromarray(rgba, mode="RGBA")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return encoded


def write_cube_viewer(
    da: xr.DataArray,
    out_html: str | Path = "cube_viewer.html",
    cmap: str = "RdBu_r",
    vmin: float | None = None,
    vmax: float | None = None,
    title: str = "Cube Viewer",
    ) -> Path:
    """Generate a standalone HTML/JS cube viewer for a 3D DataArray.

    Parameters
    ----------
    da : xr.DataArray
        3D data array with shape (time, y, x) or compatible dimension names.
    out_html : str or Path, optional
        Destination HTML file. Defaults to "cube_viewer.html".
    cmap : str, optional
        Matplotlib colormap name. Defaults to "RdBu_r".
    vmin, vmax : float, optional
        Color limits. If None, computed from the data.
    title : str, optional
        Viewer title. Defaults to "Cube Viewer".

    Returns
    -------
    Path
        Path to the written HTML file.
    """

    warn_deprecated(
        "cubedynamics.viewers.cube_viewer.write_cube_viewer",
        "cubedynamics.verbs.plot or cubedynamics.plotting.viewer.show_cube_viewer",
        since="0.2.0",
        removal="0.3.0",
    )

    time_dim, y_dim, x_dim = _infer_dims(da)

    if vmin is None:
        vmin = float(np.nanmin(da.values))
    if vmax is None:
        vmax = float(np.nanmax(da.values))

    top, front, side = _extract_faces(da, time_dim, y_dim, x_dim)

    size_time = float(da.sizes[time_dim])
    size_y = float(da.sizes[y_dim])
    size_x = float(da.sizes[x_dim])
    max_size = max(size_time, size_y, size_x)

    scale_time = size_time / max_size if max_size else 1.0
    scale_y = size_y / max_size if max_size else 1.0
    scale_x = size_x / max_size if max_size else 1.0

    top_png = _face_to_base64(top, cmap=cmap, vmin=vmin, vmax=vmax)
    front_png = _face_to_base64(front, cmap=cmap, vmin=vmin, vmax=vmax)
    side_png = _face_to_base64(side, cmap=cmap, vmin=vmin, vmax=vmax)

    with resources.files(__package__).joinpath(
        "templates/cube_viewer_template.html"
    ).open("r", encoding="utf-8") as f:
        template = f.read()

    html = (
        template.replace("__TITLE__", title)
        .replace("__TOP_TEXTURE__", top_png)
        .replace("__FRONT_TEXTURE__", front_png)
        .replace("__SIDE_TEXTURE__", side_png)
        .replace("__COLORBAR_MIN__", str(vmin))
        .replace("__COLORBAR_MAX__", str(vmax))
        .replace("__SCALE_X__", f"{scale_x:.6f}")
        .replace("__SCALE_Y__", f"{scale_time:.6f}")
        .replace("__SCALE_Z__", f"{scale_y:.6f}")
        .replace("__CD_DRIFT_CENTER_JS__", drift_centering_script())
    )

    out_path = Path(out_html)
    out_path.write_text(html, encoding="utf-8")
    return out_path


__all__ = ["write_cube_viewer"]
