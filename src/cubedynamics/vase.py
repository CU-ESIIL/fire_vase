"""Time-varying vase polygons and masking utilities."""

from __future__ import annotations

import datetime as _dt
import math

from dataclasses import dataclass
from typing import List, Union

import numpy as np
import xarray as xr
from shapely.geometry import Point, Polygon
from shapely.prepared import prep

TimeLike = Union[np.datetime64, float, int, _dt.datetime, _dt.date]

__all__ = [
    "VaseSection",
    "VaseDefinition",
    "VasePanel",
    "build_vase_mask",
    "build_vase_panels",
    "extract_vase_from_attrs",
]


@dataclass
class VaseSection:
    """Single cross-section of a vase at a given time.

    The polygon is defined in `(x, y)` space while ``time`` is a separate axis,
    allowing the same geometry vocabulary across cubes. Sections can be listed
    in any order; ``VaseDefinition`` will sort them by time.
    """

    time: TimeLike
    polygon: Polygon


@dataclass
class VaseDefinition:
    """Collection of vase sections with interpolation rules.

    The sections describe how a 2-D polygon cross-section should evolve through
    time, creating a 3-D "vase volume" once lofted across the cube. ``interp``
    controls whether polygons are snapped to the nearest timestamp or
    interpolated vertex-by-vertex (when shapes share the same vertex layout).
    """

    sections: List[VaseSection]
    interp: str = "nearest"

    def __post_init__(self) -> None:
        if not self.sections:
            raise ValueError("VaseDefinition requires at least one VaseSection")

        for sec in self.sections:
            if not isinstance(sec.polygon, Polygon):
                raise TypeError("Each section polygon must be a shapely Polygon")
            if not sec.polygon.is_valid:
                raise ValueError("Polygon provided in VaseSection is not valid")

        self.sections = sorted(self.sections, key=lambda s: s.time)

    def sorted_sections(self) -> "VaseDefinition":
        """Return a new VaseDefinition with sections sorted by time."""

        sorted_secs = sorted(self.sections, key=lambda s: s.time)
        return VaseDefinition(sorted_secs, interp=self.interp)


@dataclass
class VasePanel:
    """Rectangular patch approximating a vase hull segment.

    Coordinates are normalized to the cube space [0, 1] along each axis.
    """

    x: float
    y: float
    z: float
    width: float
    height: float
    yaw: float


def _polygon_at_time(vase: VaseDefinition, t: TimeLike) -> Polygon:
    """Return the polygon cross-section for a target time ``t``.

    For ``nearest`` interpolation the polygon from the nearest section is
    returned. For ``linear`` interpolation, polygons are interpolated vertex by
    vertex between the bracketing sections. When ``t`` is outside the provided
    time range, the nearest section polygon is used. ``t`` can be numeric or
    datetime-like, matching the cube's time coordinate type.
    """

    vase_sorted = vase.sorted_sections()
    sections = vase_sorted.sections
    times = np.array([sec.time for sec in sections])

    if vase_sorted.interp not in {"nearest", "linear"}:
        raise ValueError("interp must be either 'nearest' or 'linear'")

    if vase_sorted.interp == "nearest" or len(sections) == 1:
        idx = int(np.abs(times - t).argmin())
        return sections[idx].polygon

    # linear interpolation
    if t <= times[0]:
        return sections[0].polygon
    if t >= times[-1]:
        return sections[-1].polygon

    idx_upper = int(np.searchsorted(times, t, side="right"))
    idx_lower = idx_upper - 1
    t0 = times[idx_lower]
    t1 = times[idx_upper]
    sec0 = sections[idx_lower].polygon
    sec1 = sections[idx_upper].polygon

    coords0 = np.asarray(sec0.exterior.coords)
    coords1 = np.asarray(sec1.exterior.coords)
    if coords0.shape != coords1.shape:
        raise ValueError("Polygons for linear interpolation must share vertex layout")

    ratio = float((t - t0) / (t1 - t0)) if t1 != t0 else 0.0
    interp_coords = coords0 + ratio * (coords1 - coords0)
    return Polygon(interp_coords)


def _sample_polygon_boundary(polygon: Polygon, n_samples: int) -> np.ndarray:
    """Sample ``n_samples`` equally spaced points along the polygon boundary."""

    n_samples = max(4, int(n_samples))
    length = polygon.exterior.length
    distances = np.linspace(0, length, num=n_samples, endpoint=False)
    points = [polygon.exterior.interpolate(d).coords[0] for d in distances]
    return np.asarray(points)


def _to_numeric_time(t: TimeLike) -> float:
    """Convert datetime-like or numeric time to a float for normalization."""

    if isinstance(t, np.datetime64):
        return float(t.astype("datetime64[ns]").astype("int64"))
    if isinstance(t, (_dt.datetime, _dt.date)):
        return float(np.datetime64(t).astype("datetime64[ns]").astype("int64"))
    return float(t)


def _normalize_value(value: TimeLike, vmin: TimeLike, vmax: TimeLike) -> float:
    """Normalize ``value`` to [0, 1] between vmin and vmax, handling datetimes."""

    v_num = _to_numeric_time(value)
    vmin_num = _to_numeric_time(vmin)
    vmax_num = _to_numeric_time(vmax)
    if vmax_num == vmin_num:
        return 0.5
    return (v_num - vmin_num) / (vmax_num - vmin_num)


def build_vase_panels(
    vase: VaseDefinition,
    time_min: float,
    time_max: float,
    *,
    angle_samples: int = 24,
) -> List[VasePanel]:
    """Approximate the vase hull with rectangular panels.

    The panels are laid out by sampling each section's polygon boundary and
    connecting successive time slices, producing a coarse mesh aligned to the
    cube's normalized coordinate system.
    """

    sections = vase.sorted_sections().sections
    if len(sections) < 2:
        return []

    # Gather bounds for normalization
    all_coords = np.vstack([np.asarray(sec.polygon.exterior.coords) for sec in sections])
    x_min, y_min = all_coords[:, 0].min(), all_coords[:, 1].min()
    x_max, y_max = all_coords[:, 0].max(), all_coords[:, 1].max()

    panels: List[VasePanel] = []

    for lower, upper in zip(sections[:-1], sections[1:]):
        pts_lower = _sample_polygon_boundary(lower.polygon, angle_samples)
        pts_upper = _sample_polygon_boundary(upper.polygon, angle_samples)

        t0_norm = _normalize_value(lower.time, time_min, time_max)
        t1_norm = _normalize_value(upper.time, time_min, time_max)

        for idx in range(angle_samples):
            i_next = (idx + 1) % angle_samples
            p0 = pts_lower[idx]
            p1 = pts_lower[i_next]
            p2 = pts_upper[i_next]
            p3 = pts_upper[idx]

            mid_lower = 0.5 * (p0 + p1)
            mid_upper = 0.5 * (p3 + p2)
            center_xy = 0.5 * (mid_lower + mid_upper)

            width_vec = mid_lower - mid_upper
            width = float(np.linalg.norm(width_vec))
            height = float(abs(t1_norm - t0_norm))

            x_norm = _normalize_value(center_xy[0], x_min, x_max)
            y_norm = _normalize_value(center_xy[1], y_min, y_max)
            z_norm = 0.5 * (t0_norm + t1_norm)

            yaw = math.degrees(math.atan2(width_vec[1], width_vec[0])) if width > 0 else 0.0

            panels.append(
                VasePanel(
                    x=x_norm,
                    y=y_norm,
                    z=z_norm,
                    width=_normalize_value(width, 0.0, max(x_max - x_min, y_max - y_min)),
                    height=height,
                    yaw=yaw,
                )
            )

    return panels


def build_vase_mask(
    cube: xr.DataArray,
    vase: VaseDefinition,
    time_dim: str = "time",
    y_dim: str = "y",
    x_dim: str = "x",
) -> xr.DataArray:
    """Build a boolean mask for voxels inside a time-varying vase.

    A **vase volume** is formed by lofting time-stamped polygons through the
    cube's time axis. This helper evaluates the appropriate polygon for each
    time coordinate and marks `(y, x)` locations that fall inside it.

    Notes
    -----
    - The mask matches ``cube`` shape over ``(time, y, x)`` and carries the name
      ``"vase_mask"``.
    - Computation streams over time slices using coordinate arrays only (no
      ``cube.values``), keeping memory use low and working with dask-backed
      cubes or ``VirtualCube`` sources.
    """

    for dim in (time_dim, y_dim, x_dim):
        if dim not in cube.dims:
            raise ValueError(f"Dimension {dim!r} not found in cube dims: {cube.dims}")

    times = cube.coords[time_dim].values
    ys = cube.coords[y_dim].values
    xs = cube.coords[x_dim].values

    mask_slices = []
    for t in times:
        polygon = _polygon_at_time(vase, t)
        prepared = prep(polygon)
        slice_mask = np.zeros((len(ys), len(xs)), dtype=bool)
        for j, y in enumerate(ys):
            for k, x in enumerate(xs):
                pt = Point(x, y)
                slice_mask[j, k] = prepared.intersects(pt)
        mask_slices.append(slice_mask)

    mask_np = np.stack(mask_slices, axis=0)
    mask = xr.DataArray(
        data=mask_np,
        coords={time_dim: cube.coords[time_dim], y_dim: cube.coords[y_dim], x_dim: cube.coords[x_dim]},
        dims=(time_dim, y_dim, x_dim),
        name="vase_mask",
    )
    mask.attrs["description"] = "Boolean mask for vase volume"
    return mask


def extract_vase_from_attrs(da: xr.DataArray):
    """
    Return the VaseDefinition attached to this DataArray, if any.

    ``v.vase_extract`` stores it in ``attrs["vase"]``.
    """

    return da.attrs.get("vase", None)
