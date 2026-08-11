"""Vase visualization utilities for scientific 3-D workflows.

These helpers are intentionally decoupled from the CSS-based cube viewer and
focus on notebook/research usage with optional PyVista/Trimesh dependencies.
"""

from __future__ import annotations

import numpy as np
import xarray as xr

from .vase import VaseDefinition


def _validate_dims(cube: xr.DataArray, dims: tuple[str, str, str]) -> None:
    for dim in dims:
        if dim not in cube.dims:
            raise ValueError(f"Dimension {dim!r} not found in cube dims: {cube.dims}")


def extract_vase_points(
    cube: xr.DataArray,
    mask: xr.DataArray,
    time_dim: str = "time",
    y_dim: str = "y",
    x_dim: str = "x",
):
    """Extract coordinates and values for voxels where ``mask`` is ``True``.

    Returns a dict:
        {
            "time": np.ndarray,
            "y":    np.ndarray,
            "x":    np.ndarray,
            "value": np.ndarray,
        }

    The mask should come from :func:`cubedynamics.vase.build_vase_mask` (or
    :func:`cubedynamics.verbs.vase.vase_mask`), keeping visualization aligned
    with the grammar/cube viewer overlays.

    This MUST be streaming-friendly:
        - Do not call cube.values on the full cube.
        - Use cube.where(mask).stack or .to_dataframe(dropna=True).
    """

    _validate_dims(cube, (time_dim, y_dim, x_dim))

    masked = cube.where(mask)
    df = masked.to_dataframe(name="value").dropna()

    times = df.index.get_level_values(time_dim).to_numpy()
    ys = df.index.get_level_values(y_dim).to_numpy()
    xs = df.index.get_level_values(x_dim).to_numpy()
    values = df["value"].to_numpy()

    return {"time": times, "y": ys, "x": xs, "value": values}


def _convert_time_to_numeric(t: np.ndarray) -> np.ndarray:
    if t.dtype.kind in ("M", "m"):
        return t.astype("datetime64[ns]").astype(float) / 1e9
    return t.astype(float)


def vase_scatter_plot(
    cube: xr.DataArray,
    mask: xr.DataArray,
    *,
    time_dim: str = "time",
    y_dim: str = "y",
    x_dim: str = "x",
    cmap: str = "viridis",
    point_size: float = 3.0,
    render_points_as_spheres: bool = True,
):
    """3-D scientific scatter plot of voxels inside the vase.

    Requires ``pyvista`` and consumes the same vase mask used by the
    grammar-of-graphics viewer. Raise ``ImportError`` if ``pyvista`` is not
    installed.

    Axes:
        x-axis = cube[x_dim]
        y-axis = cube[y_dim]
        z-axis = cube[time_dim] (or numeric index if datetime)
    """

    try:
        import pyvista as pv
    except ImportError as exc:  # pragma: no cover - exercised via importorskip
        raise ImportError("vase_scatter_plot requires pyvista.") from exc

    points_dict = extract_vase_points(
        cube,
        mask,
        time_dim=time_dim,
        y_dim=y_dim,
        x_dim=x_dim,
    )

    t_numeric = _convert_time_to_numeric(points_dict["time"])
    points = np.column_stack([points_dict["x"], points_dict["y"], t_numeric])
    values = points_dict["value"]

    cloud = pv.PolyData(points)
    cloud["value"] = values

    plotter = pv.Plotter()
    plotter.add_mesh(
        cloud,
        scalars="value",
        cmap=cmap,
        render_points_as_spheres=render_points_as_spheres,
        point_size=point_size,
    )
    plotter.show()


def vase_to_mesh(
    vase: VaseDefinition,
    *,
    time_scale: float = 1.0,
):
    """Convert VaseDefinition into a 3-D mesh using a sweep (loft) of polygons.

    Requires ``trimesh`` and mirrors the vase geometry used by the cube viewer
    and verbs. This is an optional scientific helper and not required for
    standard CubePlot usage.

    - time_scale rescales time → z-axis.
    - Polygons are assumed to have identical vertex order for interpolation.
    """

    try:
        import trimesh
    except ImportError as exc:  # pragma: no cover - exercised via importorskip
        raise ImportError("vase_to_mesh requires trimesh.") from exc

    vase_sorted = vase.sorted_sections()
    sections = vase_sorted.sections

    if not sections:
        raise ValueError("VaseDefinition must include at least one section")

    path = []
    polygons = []
    for sec in sections:
        path.append([0.0, 0.0, float(sec.time) * time_scale])
        poly_coords = np.asarray(sec.polygon.exterior.coords)
        polygons.append(poly_coords[:, :2])

    sweep_path = np.asarray(path)
    mesh = trimesh.creation.sweep_polygon(polygons, sweep_path)
    return mesh


def vase_scatter_with_hull(
    cube: xr.DataArray,
    mask: xr.DataArray,
    vase: VaseDefinition,
    *,
    time_dim: str = "time",
    y_dim: str = "y",
    x_dim: str = "x",
    cmap: str = "viridis",
    point_size: float = 3.0,
    render_points_as_spheres: bool = True,
    hull_opacity: float = 0.2,
):
    """Overlay vase scatter points with a translucent hull mesh.

    Combines PyVista scatter rendering with a ``trimesh``-derived hull when both
    optional dependencies are available, using the same mask produced by
    :func:`cubedynamics.vase.build_vase_mask`.
    """

    try:
        import pyvista as pv
    except ImportError as exc:  # pragma: no cover - exercised via importorskip
        raise ImportError("vase_scatter_with_hull requires pyvista.") from exc

    hull_mesh = vase_to_mesh(vase)

    points_dict = extract_vase_points(
        cube,
        mask,
        time_dim=time_dim,
        y_dim=y_dim,
        x_dim=x_dim,
    )

    t_numeric = _convert_time_to_numeric(points_dict["time"])
    scatter_points = np.column_stack([points_dict["x"], points_dict["y"], t_numeric])
    values = points_dict["value"]

    cloud = pv.PolyData(scatter_points)
    cloud["value"] = values

    plotter = pv.Plotter()
    plotter.add_mesh(
        cloud,
        scalars="value",
        cmap=cmap,
        render_points_as_spheres=render_points_as_spheres,
        point_size=point_size,
    )

    hull = pv.wrap(hull_mesh)
    plotter.add_mesh(hull, opacity=hull_opacity, color="white")
    plotter.show()
