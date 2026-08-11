from __future__ import annotations

"""
Self-contained helpers for fire time-hull geometry and GRIDMET climate sampling.

This module intentionally avoids importing cubedynamics internals to steer clear
of circular imports. It contains lightweight dataclasses and utilities adapted
from the fire/time-hull prototype used in notebooks.
"""

from dataclasses import dataclass, field, replace
import shutil
import tempfile
from pathlib import Path
import zipfile
import warnings
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
import plotly.graph_objects as go
import requests
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep


def _union_all(geoms):
    try:
        from shapely import union_all  # type: ignore

        return union_all(geoms)
    except Exception:
        return unary_union(geoms)


def log(verbose: bool, *args) -> None:
    if verbose:
        print(*args)


@dataclass
class TemporalSupport:
    """Simple description of temporal coverage for a dataset."""

    start: pd.Timestamp
    end: pd.Timestamp

    def contains(self, start: pd.Timestamp, end: pd.Timestamp) -> bool:
        return pd.Timestamp(start) >= self.start and pd.Timestamp(end) <= self.end


GRIDMET_SUPPORT = TemporalSupport(
    start=pd.Timestamp("1979-01-01"), end=pd.Timestamp("2100-01-01")
)


_FIRED_FILE_MAP = {
    ("events", "gpkg"): "fired_conus-ak_events_nov2001-march2021.gpkg",
    ("events", "shp"): "fired_conus-ak_events_nov2001-march2021.shp",
    ("daily", "gpkg"): "fired_conus-ak_daily_nov2001-march2021.gpkg",
    ("daily", "shp"): "fired_conus-ak_daily_nov2001-march2021.shp",
}


def _download_and_extract_fired_to_cache(
    *,
    which: str,
    prefer: str,
    out_path: Path,
    dataset_page: str,
    download_id: str,
    timeout: int,
) -> None:
    assert which in ("events", "daily")
    assert prefer in ("gpkg", "shp")

    primary_name = _FIRED_FILE_MAP[(which, prefer)]
    alt_ext = "shp" if prefer == "gpkg" else "gpkg"
    alt_name = _FIRED_FILE_MAP[(which, alt_ext)]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Referer": dataset_page,
        "Connection": "keep-alive",
    }

    session = requests.Session()
    r0 = session.get(dataset_page, headers=headers, timeout=timeout)
    if r0.status_code not in (200, 304):
        warnings.warn(
            f"FIRED landing page returned HTTP {r0.status_code}; "
            "continuing with direct ZIP download."
        )

    zip_url = f"https://scholar.colorado.edu/downloads/{download_id}"
    resp = session.get(
        zip_url,
        headers=headers,
        stream=True,
        timeout=timeout,
        allow_redirects=True,
    )

    content_type = resp.headers.get("Content-Type", "")
    if "html" in content_type.lower():
        raise RuntimeError(
            "Expected FIRED ZIP download but received HTML; check network/proxy/auth."
        )

    resp.raise_for_status()

    with tempfile.TemporaryDirectory() as tmpdir:
        zpath = Path(tmpdir) / "fired.zip"
        with open(zpath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)

        with zipfile.ZipFile(zpath, "r") as zf:
            names = zf.namelist()
            chosen = None
            for cand in (primary_name, alt_name):
                if cand in names:
                    chosen = cand
                    break

            if chosen is None:
                for name in names:
                    if which in name and (name.endswith(".gpkg") or name.endswith(".shp")):
                        chosen = name
                        break

            if chosen is None:
                raise RuntimeError(
                    f"Could not find FIRED file inside ZIP for {which} "
                    f"(tried {primary_name!r} and {alt_name!r})."
                )

            extraction_dir = Path(tmpdir) / "extracted"
            extraction_dir.mkdir(parents=True, exist_ok=True)

            zf.extract(chosen, path=extraction_dir)
            chosen_path = extraction_dir / chosen
            dest_parent = out_path.parent
            dest_name = Path(chosen).name
            dest_path = dest_parent / dest_name

            if chosen_path.suffix == ".shp":
                base_stem = Path(chosen).stem
                parent_rel = Path(chosen).parent
                shap_members = [
                    name
                    for name in names
                    if Path(name).parent == parent_rel and Path(name).stem == base_stem
                ]
                for member in shap_members:
                    member_path = extraction_dir / member
                    if not member_path.exists():
                        zf.extract(member, path=extraction_dir)
                    dest_member = dest_parent / Path(member).name
                    dest_member.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(member_path, dest_member)
            else:
                dest_parent.mkdir(parents=True, exist_ok=True)
                shutil.move(chosen_path, dest_path)

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    if not dest_path.exists():
        raise FileNotFoundError(f"Expected FIRED file at {dest_path} after download.")


def load_fired_conus_ak(
    which: str = "daily",
    prefer: str = "gpkg",
    cache_dir: str | Path | None = None,
    *,
    download: bool = False,
    dataset_page: str = "https://scholar.colorado.edu/concern/datasets/d504rm74m",
    download_id: str = "h702q749s",
    timeout: int = 180,
) -> gpd.GeoDataFrame:
    """
    Load FIRED CONUS+AK polygons from a local cache, with optional download.

    Expected layout (default):

        ~/.fired_cache/
            fired_conus-ak_daily_nov2001-march2021.gpkg
            fired_conus-ak_events_nov2001-march2021.gpkg  (optional)

    Parameters
    ----------
    which : {"events", "daily"}
        Which FIRED layer to load.
    prefer : {"gpkg", "shp"}
        Preferred file format to load; falls back to the alternate format if
        the ZIP download is missing the preferred one.
    cache_dir :
        Optional override for the cache directory. Defaults to
        Path.home() / ".fired_cache".
    download : bool
        If True, stream the FIRED ZIP from CU Scholar when the expected cache
        file is missing, then cache and load it. Defaults to False to preserve
        cache-only behavior.
    dataset_page : str
        Landing page for the FIRED dataset on CU Scholar. Used to prime
        cookies before download.
    download_id : str
        Download token for the FIRED ZIP on CU Scholar.
    timeout : int
        Timeout (seconds) for HTTP requests when download=True.

    Returns
    -------
    GeoDataFrame
        FIRED layer reprojected to EPSG:4326.

    Raises
    ------
    FileNotFoundError
        If the expected FIRED file is not found in the cache directory.
        In that case, download the FIRED GPKG from CU Scholar on a
        machine with access, copy it into the cache directory, and then
        rerun this function. Set download=True to have this function attempt
        the download automatically.
    """
    if which not in {"daily", "events"}:
        raise ValueError("which must be 'daily' or 'events'")
    if prefer not in {"gpkg", "shp"}:
        raise ValueError("prefer must be 'gpkg' or 'shp'")

    cache_dir = Path(cache_dir or (Path.home() / ".fired_cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)

    path = cache_dir / _FIRED_FILE_MAP[(which, prefer)]
    alt_ext = "shp" if prefer == "gpkg" else "gpkg"
    alt_path = cache_dir / _FIRED_FILE_MAP[(which, alt_ext)]
    if not path.exists():
        if not download:
            raise FileNotFoundError(
                f"FIRED file not found at {path}\n\n"
                "To use `load_fired_conus_ak` in this environment:\n"
                "  1. On a machine with browser/access to CU Scholar, download the\n"
                "     appropriate FIRED GPKG (e.g., fired_conus-ak_daily_nov2001-march2021.gpkg).\n"
                "  2. Copy that file into this environment at:\n"
                f"       {path}\n"
                "  3. Rerun this function.\n"
            )

        _download_and_extract_fired_to_cache(
            which=which,
            prefer=prefer,
            out_path=path,
            dataset_page=dataset_page,
            download_id=download_id,
            timeout=timeout,
        )
        if not path.exists() and alt_path.exists():
            path = alt_path
        elif not path.exists():
            raise FileNotFoundError(f"Expected FIRED file at {path} after download.")

    gdf = gpd.read_file(path)
    if gdf.crs:
        gdf = gdf.to_crs("EPSG:4326")
    else:
        gdf = gdf.set_crs("EPSG:4326")
    return gdf


@dataclass
class FireEventDaily:
    """Canonical daily fire event object built from FIRED-like perimeters."""

    event_id: Any
    gdf: gpd.GeoDataFrame
    t0: pd.Timestamp
    t1: pd.Timestamp
    centroid_lat: float
    centroid_lon: float

    @classmethod
    def from_fired(
        cls,
        fired_daily: gpd.GeoDataFrame,
        event_id: Any,
        *,
        date_col: str = "date",
    ) -> "FireEventDaily":
        """Construct a canonical event bundle from FIRED daily perimeters."""

        return build_fire_event_daily(
            fired_daily=fired_daily,
            event_id=event_id,
            date_col=date_col,
        )

    @classmethod
    def example(cls) -> "FireEventDaily":
        """Return a tiny synthetic event for tests, docs, and lightweight demos."""

        rows = []
        for day, scale in enumerate((0.10, 0.16, 0.22), start=0):
            rows.append(
                {
                    "id": 1,
                    "date": pd.Timestamp("2020-07-01") + pd.Timedelta(days=day),
                    "geometry": Polygon(
                        [
                            (-105.10, 40.00),
                            (-105.10 + scale, 40.00),
                            (-105.10 + scale, 40.00 + scale),
                            (-105.10, 40.00 + scale),
                        ]
                    ),
                }
            )
        gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
        return cls.from_fired(gdf, event_id=1)

    @property
    def duration_days(self) -> int:
        """Inclusive event duration in days."""

        return int((pd.Timestamp(self.t1) - pd.Timestamp(self.t0)).days) + 1

    @property
    def daily_perimeters(self) -> gpd.GeoDataFrame:
        """Return the cleaned daily perimeter table backing the event."""

        return self.gdf

    def to_hull(self, **kwargs) -> "FireHull":
        """Build the canonical fire-time hull for this event."""

        return compute_time_hull_geometry(self, **kwargs)


class HullMetrics(dict):
    """Stable, dictionary-like fire hull metrics with a callable summary hook."""

    def __call__(self) -> dict[str, float]:
        return dict(self)


@dataclass
class FireHull:
    """Canonical fire-time hull / VASE object for event geometry and attribution."""

    event: FireEventDaily
    verts_km: np.ndarray
    tris: np.ndarray
    t_days_vert: np.ndarray
    t_norm_vert: np.ndarray
    metrics: HullMetrics
    environment: dict[str, "HullEnvironmentField"] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.metrics, HullMetrics):
            self.metrics = HullMetrics(self.metrics)

    def to_mesh(self) -> dict[str, np.ndarray]:
        """Return the current triangulated mesh representation."""

        return {
            "verts_km": np.asarray(self.verts_km, dtype=float),
            "tris": np.asarray(self.tris, dtype=int),
            "t_days_vert": np.asarray(self.t_days_vert, dtype=float),
            "t_norm_vert": np.asarray(self.t_norm_vert, dtype=float),
        }

    def to_cube(self, template: xr.DataArray | None = None) -> xr.DataArray:
        """Return a boolean occupancy cube for this hull when a template cube is provided.

        Parameters
        ----------
        template
            DataArray supplying target ``(time, y, x)`` coordinates. This keeps
            the conversion cube-compatible without inventing arbitrary grids.

        Raises
        ------
        NotImplementedError
            If no template cube is supplied. Full free-standing hull-to-cube
            generation remains a follow-up task.
        """

        if template is None:
            raise NotImplementedError(
                "FireHull.to_cube currently requires a template DataArray with "
                "time/y/x coordinates. TODO: add standalone occupancy-grid generation."
            )

        from .vase import VaseDefinition, VaseSection, build_vase_mask

        sections = [
            VaseSection(time=pd.Timestamp(row.date).to_datetime64(), polygon=_largest_polygon(row.geometry))
            for row in self.event.gdf.itertuples(index=False)
            if _largest_polygon(row.geometry) is not None
        ]
        vase = VaseDefinition(sections)
        mask = build_vase_mask(template, vase)
        mask.attrs["fire_event_id"] = self.event.event_id
        mask.attrs["description"] = "Boolean occupancy cube derived from FireHull"
        return mask

    def attach_environment(
        self,
        cube: xr.DataArray | xr.Dataset | "ClimateCube",
        *,
        variables: Sequence[str] | None = None,
        method: str = "nearest",
    ) -> "FireHull":
        """Attach per-variable environmental attribution summaries to the hull.

        The current implementation samples per-day values inside/outside the
        event footprint, then explicitly projects those slice values onto hull
        vertices. This keeps the summary view and the mesh-aligned view
        synchronized while leaving room for richer local projection later.
        """

        if method != "nearest":
            raise NotImplementedError(
                "FireHull.attach_environment currently supports method='nearest' only."
            )

        if isinstance(cube, ClimateCube):
            data_vars: Mapping[str, xr.DataArray] = {cube.da.name or "value": cube.da}
        elif isinstance(cube, xr.DataArray):
            data_vars = {cube.name or "value": cube}
        elif isinstance(cube, xr.Dataset):
            chosen = list(variables) if variables is not None else list(cube.data_vars)
            data_vars = {name: cube[name] for name in chosen}
        else:
            raise TypeError("cube must be a DataArray, Dataset, or ClimateCube")

        chosen_names = list(variables) if variables is not None else list(data_vars)
        summaries = dict(self.environment)
        for name in chosen_names:
            if name not in data_vars:
                raise KeyError(f"Variable {name!r} not present in environmental cube")
            summary = build_inside_outside_climate_samples(
                self.event,
                ClimateCube(da=data_vars[name]),
            )
            layer_dates, layer_values, vertex_values, vertex_slice_index = _summary_to_vertex_values(
                self,
                summary,
            )
            summaries[name] = HullEnvironmentField(
                variable=name,
                method=method,
                summary=summary,
                layer_dates=layer_dates,
                layer_values=layer_values,
                vertex_values=vertex_values,
                vertex_slice_index=vertex_slice_index,
            )

        return replace(self, environment=summaries)

    def plot(
        self,
        *,
        color: str | None = None,
        summary: "HullClimateSummary | None" = None,
        cube: xr.DataArray | xr.Dataset | "ClimateCube | None" = None,
        method: str = "nearest",
        **kwargs,
    ) -> go.Figure:
        """Plot the hull using either attached or supplied environmental data."""

        if summary is None and cube is not None:
            enriched = self.attach_environment(cube, variables=[color] if color else None, method=method)
            field = enriched.environment[color or next(iter(enriched.environment))]
            summary = field.summary
            values = field.vertex_values
        elif summary is None:
            if color and color in self.environment:
                field = self.environment[color]
                summary = field.summary
                values = field.vertex_values
            elif len(self.environment) == 1:
                field = next(iter(self.environment.values()))
                summary = field.summary
                values = field.vertex_values
            else:
                values = None
        else:
            values = None

        if summary is None:
            raise ValueError(
                "FireHull.plot requires a HullClimateSummary, an attached environment "
                "variable, or a cube to sample."
            )

        var_label = kwargs.pop("var_label", color or "value")
        return plot_climate_filled_hull(self, summary, values=values, var_label=var_label, **kwargs)


TimeHull = FireHull


@dataclass
class Vase:
    """Vase-like container derived from a ``TimeHull`` for visualization."""

    verts_km: np.ndarray
    tris: np.ndarray
    metadata: Dict[str, Any]


@dataclass
class ClimateCube:
    da: xr.DataArray


@dataclass
class HullClimateSummary:
    values_inside: np.ndarray
    values_outside: np.ndarray
    per_day_mean: pd.Series


@dataclass
class HullEnvironmentField:
    """Explicit environmental attribution aligned to a hull mesh.

    Parameters
    ----------
    variable
        Environmental variable name, e.g. ``"vpd"``.
    method
        Attribution method used to derive the values. Currently ``"nearest"``.
    summary
        Summary-level inside/outside sampling results retained for compatibility
        and quick distribution plots.
    layer_dates
        Calendar date assigned to each hull layer.
    layer_values
        Per-layer environmental values aligned to ``layer_dates``.
    vertex_values
        Per-vertex environmental values projected onto the hull mesh.
    vertex_slice_index
        Explicit mapping from each vertex to its time-layer index.
    """

    variable: str
    method: str
    summary: HullClimateSummary
    layer_dates: pd.DatetimeIndex
    layer_values: np.ndarray
    vertex_values: np.ndarray
    vertex_slice_index: np.ndarray


def _make_hull_metrics(
    *,
    scale_km: float,
    days: float,
    hull_volume_km2_days: float,
    hull_surface_km_day: float,
    footprint_area_series_km2: Sequence[float] | None = None,
) -> HullMetrics:
    """Return stable hull metric names plus legacy aliases.

    Units
    -----
    - ``duration_days`` / ``days``: day counts
    - ``scale_km``: characteristic radial scale in kilometers
    - ``footprint_area_*_km2``: area in square kilometers
    - ``hull_volume_km2_days`` / ``volume_km2_days``: area-time volume
    - ``hull_surface_km_day`` / ``surface_km_day``: surface area in km·day
    """

    footprint = np.asarray(footprint_area_series_km2 if footprint_area_series_km2 is not None else [], dtype=float)
    metrics = HullMetrics(
        {
            "duration_days": float(days),
            "days": float(days),  # legacy alias
            "scale_km": float(scale_km),
            "footprint_area_peak_km2": float(np.nanmax(footprint)) if footprint.size else float("nan"),
            "footprint_area_final_km2": float(footprint[-1]) if footprint.size else float("nan"),
            "hull_volume_km2_days": float(hull_volume_km2_days),
            "volume_km2_days": float(hull_volume_km2_days),  # legacy alias
            "hull_surface_km_day": float(hull_surface_km_day),
            "surface_km_day": float(hull_surface_km_day),  # legacy alias
        }
    )
    return metrics


def normalize_dates(values) -> pd.DatetimeIndex:
    result = pd.to_datetime(values, errors="coerce")

    # Series and array-likes expose ``dt`` for datetime operations
    if hasattr(result, "dt"):
        return result.dt.normalize()

    # DatetimeIndex has a dedicated ``normalize`` method
    if hasattr(result, "normalize"):
        return result.normalize()

    # Scalar timestamps also provide ``normalize``; coerce to DatetimeIndex otherwise
    ts = pd.to_datetime([result], errors="coerce")
    return ts.normalize()


def clean_event_daily_rows(
    gdf_daily: gpd.GeoDataFrame,
    event_id,
    id_col: str = "id",
    date_col: str = "date",
) -> Optional[gpd.GeoDataFrame]:
    eg = gdf_daily[gdf_daily[id_col] == event_id].copy()
    if eg.empty:
        return None

    eg[date_col] = normalize_dates(eg[date_col])
    eg = eg.sort_values(date_col)

    rows: list[pd.Series] = []
    last_geom = None

    for _, row in eg.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        try:
            if isinstance(geom, MultiPolygon):
                geom = unary_union(geom)
        except Exception:
            pass

        if last_geom is not None and geom.equals(last_geom):
            continue

        r_copy = row.copy()
        r_copy.geometry = geom
        rows.append(r_copy)
        last_geom = geom

    if not rows:
        return None

    out = gpd.GeoDataFrame(rows, crs=gdf_daily.crs).reset_index(drop=True)
    return out


def _largest_polygon(geom) -> Optional[Polygon]:
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        polys = [p for p in geom.geoms if isinstance(p, Polygon)]
        if not polys:
            return None
        return max(polys, key=lambda p: p.area)
    return None


def _sample_ring_equal_steps(poly: Polygon, n_samples: int = 100) -> Optional[np.ndarray]:
    if poly is None or poly.is_empty:
        return None

    ring = LineString(poly.exterior.coords)
    if len(ring.coords) > 1 and ring.coords[0] == ring.coords[-1]:
        ring = LineString(list(ring.coords)[:-1])

    L = ring.length
    if not np.isfinite(L) or L <= 0:
        return None

    distances = np.linspace(0.0, L, n_samples, endpoint=False)
    coords = [ring.interpolate(d) for d in distances]
    return np.array([[p.x, p.y] for p in coords], dtype=float)


def _tri_area(p1, p2, p3) -> float:
    a = np.asarray(p2) - np.asarray(p1)
    b = np.asarray(p3) - np.asarray(p1)
    cross = np.cross(a, b)
    return 0.5 * float(np.linalg.norm(cross))


def pick_event_with_joint_support(
    fired_daily: gpd.GeoDataFrame,
    *,
    climate_support: TemporalSupport,
    time_buffer_days: int = 0,
    min_days: int = 3,
    id_col: str = "id",
    date_col: str = "date",
) -> Any:
    for eid in fired_daily[id_col].unique():
        eg = clean_event_daily_rows(fired_daily, eid, id_col=id_col, date_col=date_col)
        if eg is None or eg.empty:
            continue
        dates = pd.to_datetime(eg[date_col], errors="coerce").dt.normalize()
        if dates.nunique() < min_days:
            continue
        start = dates.min() - pd.Timedelta(days=time_buffer_days)
        end = dates.max() + pd.Timedelta(days=time_buffer_days)
        if climate_support.contains(start, end):
            return eid
    raise ValueError("No event found with requested joint temporal support")


def build_fire_event_daily(
    *,
    fired_daily: Optional[gpd.GeoDataFrame] = None,
    event_id=None,
    fired_event: Optional[FireEventDaily] = None,
    date_col: str = "date",
) -> FireEventDaily:
    if fired_event is not None:
        return fired_event

    if fired_daily is None or event_id is None:
        raise ValueError("fired_daily and event_id are required when fired_event is not provided")

    eg_clean = clean_event_daily_rows(fired_daily, event_id, id_col="id", date_col=date_col)
    if eg_clean is None or eg_clean.empty:
        raise ValueError(f"No usable daily perimeters found for event_id={event_id!r}")

    if eg_clean.crs is None:
        eg_clean = eg_clean.set_crs("EPSG:4326")
    elif eg_clean.crs.to_string().upper() != "EPSG:4326":
        eg_clean = eg_clean.to_crs("EPSG:4326")

    dates = normalize_dates(eg_clean[date_col])
    t0 = dates.min()
    t1 = dates.max()

    union_geom = _union_all(eg_clean.geometry.values)
    centroid = union_geom.centroid
    centroid_lat = float(centroid.y)
    centroid_lon = float(centroid.x)

    return FireEventDaily(
        event_id=event_id,
        gdf=eg_clean,
        t0=t0,
        t1=t1,
        centroid_lat=centroid_lat,
        centroid_lon=centroid_lon,
    )


def build_fire_event(
    fired_daily: gpd.GeoDataFrame,
    event_id,
    *,
    date_col: str = "date",
) -> FireEventDaily:
    warnings.warn(
        "build_fire_event is deprecated; use build_fire_event_daily(fired_daily=..., event_id=...) instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return build_fire_event_daily(fired_daily=fired_daily, event_id=event_id, date_col=date_col)


def compute_time_hull_geometry(
    event: FireEventDaily,
    *,
    date_col: str = "date",
    z_col: str = "event_day",
    n_ring_samples: int = 100,
    n_theta: int = 96,
    crs_epsg_xy: int = 5070,
    center_each_day: bool = True,
    verbose: bool = False,
) -> TimeHull:
    """
    Build a 3-D time hull mesh from per-day fire perimeters.

    Parameters
    ----------
    event
        FIRED daily perimeter bundle produced by :func:`build_fire_event`.
    date_col
        Name of the date column in the GeoDataFrame. Dates are normalized
        to midnight before processing.
    z_col
        Column encoding monotonic time progression for the z axis. When
        missing, a sequential index is used instead.
    n_ring_samples
        Number of equally spaced samples taken along each daily perimeter.
    n_theta
        Number of angular steps for the convex hull reconstruction.
    crs_epsg_xy
        EPSG code used to project perimeter geometry for distance-preserving
        sampling. ``None`` skips reprojection and uses the input CRS.
    center_each_day
        If True, centers each perimeter ring around its own centroid before
        stacking into the hull grid.
    verbose
        If True, prints derived hull metrics for debugging.

    Returns
    -------
    TimeHull
        A mesh representation containing vertices in kilometers, triangle
        indices, normalized time coordinates, and summary metrics.

    Notes
    -----
    Geometry sampling is purely numerical and does not trigger any external
    I/O. The returned structure is ready for plotting or conversion to a
    vase via :func:`time_hull_to_vase`.

    Examples
    --------
    >>> hull = compute_time_hull_geometry(event, n_ring_samples=64, n_theta=128)
    >>> hull.metrics["surface_km_day"] > 0
    True
    """
    eg = event.gdf.copy()
    eg[date_col] = pd.to_datetime(eg[date_col], errors="coerce")
    eg = eg.sort_values(date_col).reset_index(drop=True)

    if z_col in eg.columns:
        Z = eg[z_col].to_numpy(float)
    else:
        Z = np.arange(1, len(eg) + 1, dtype=float)

    if crs_epsg_xy is not None:
        try:
            eg = eg.to_crs(epsg=crs_epsg_xy)
        except Exception:
            pass

    rings: list[np.ndarray] = []
    areas_m2: list[float] = []

    for geom in eg.geometry:
        poly = _largest_polygon(geom)
        if poly is None:
            continue

        xy = _sample_ring_equal_steps(poly, n_samples=n_ring_samples)
        if xy is None:
            continue

        if center_each_day:
            xy = xy - xy.mean(axis=0)

        rings.append(xy)
        areas_m2.append(float(poly.area))

    if len(rings) < 2:
        raise ValueError(f"Not enough valid perimeters to build a hull for event {event.event_id!r}")

    thetas = np.linspace(0.0, 2.0 * np.pi, n_theta, endpoint=False)
    U = np.stack([np.cos(thetas), np.sin(thetas)], axis=1)
    M = len(rings)
    T = n_theta

    R = np.zeros((M, T), dtype=float)
    for i, xy in enumerate(rings):
        R[i, :] = (U @ xy.T).max(axis=1)

    P_m = np.zeros((M, T, 3), dtype=float)
    P_m[:, :, 0] = R * U[None, :, 0]
    P_m[:, :, 1] = R * U[None, :, 1]
    P_m[:, :, 2] = np.array(Z[:M], float)[:, None]

    P_km = np.empty_like(P_m)
    P_km[:, :, 0] = P_m[:, :, 0] / 1000.0
    P_km[:, :, 1] = P_m[:, :, 1] / 1000.0
    P_km[:, :, 2] = P_m[:, :, 2]

    rmax_m = float(np.nanmax(np.sqrt(P_m[:, :, 0] ** 2 + P_m[:, :, 1] ** 2)))
    scale_km = rmax_m / 1000.0
    days = float(M)

    Z_use = np.array(Z[:M], float)
    areas_use = np.array(areas_m2[:M], float)
    if len(Z_use) >= 2:
        integrator = getattr(np, "trapezoid", None)
        if integrator is None:
            hull_volume_m2_days = float(np.trapz(areas_use, x=Z_use))
        else:
            hull_volume_m2_days = float(integrator(areas_use, Z_use))
    else:
        hull_volume_m2_days = 0.0
    hull_volume_km2_days = hull_volume_m2_days / 1e6

    tris: list[tuple[int, int, int]] = []
    surface = 0.0

    for i in range(M - 1):
        for j in range(T):
            jn = (j + 1) % T

            v1k = P_km[i, j]
            v2k = P_km[i, jn]
            v3k = P_km[i + 1, jn]
            v4k = P_km[i + 1, j]

            surface += _tri_area(v1k, v2k, v3k) + _tri_area(v1k, v3k, v4k)

            idx_v1 = i * T + j
            idx_v2 = i * T + jn
            idx_v3 = (i + 1) * T + jn
            idx_v4 = (i + 1) * T + j

            tris.append((idx_v1, idx_v2, idx_v3))
            tris.append((idx_v1, idx_v3, idx_v4))

    hull_surface_km_day = float(surface)

    verts_km = P_km.reshape(-1, 3)
    tris_arr = np.asarray(tris, dtype=int)

    Z_grid = np.array(Z[:M], float)[:, None] * np.ones((1, T), float)
    t_days_vert = Z_grid.ravel()
    z_min = float(Z_grid.min())
    z_max = float(Z_grid.max())
    z_rng = max(1e-9, z_max - z_min)
    t_norm_vert = (t_days_vert - z_min) / z_rng

    metrics = _make_hull_metrics(
        scale_km=scale_km,
        days=days,
        hull_volume_km2_days=hull_volume_km2_days,
        hull_surface_km_day=hull_surface_km_day,
        footprint_area_series_km2=areas_use / 1e6,
    )

    if verbose:
        print("TimeHull metrics:", metrics)

    return FireHull(
        event=event,
        verts_km=verts_km,
        tris=tris_arr,
        t_days_vert=t_days_vert,
        t_norm_vert=t_norm_vert,
        metrics=metrics,
    )


def sample_inside_outside(
    event: FireEventDaily,
    cube_da: xr.DataArray,
    *,
    date_col: str = "date",
    fast: bool = False,
    verbose: bool = False,
) -> HullClimateSummary:
    da = cube_da
    y_dim, x_dim = infer_spatial_dims(da)
    epsg = infer_epsg(da)
    if epsg is None:
        raise ValueError("Could not infer EPSG for cube; provide metadata or lat/lon dims")

    y_vals = np.asarray(da[y_dim].values)
    x_vals = np.asarray(da[x_dim].values)
    ny, nx = y_vals.size, x_vals.size

    dy = float(np.nanmedian(np.diff(y_vals))) if ny > 1 else 0.0
    dx = float(np.nanmedian(np.diff(x_vals))) if nx > 1 else 0.0
    dy = abs(dy)
    dx = abs(dx)

    dates_clim = normalize_dates(da["time"].values)
    event_gdf = event.gdf.copy()
    event_gdf["date_norm"] = normalize_dates(event_gdf[date_col])
    cube_crs = f"EPSG:{epsg}"
    if event_gdf.crs is None:
        event_gdf = event_gdf.set_crs("EPSG:4326")
    if event_gdf.crs.to_string().upper() != cube_crs.upper():
        event_gdf = event_gdf.to_crs(cube_crs)

    half_dx = dx / 2.0 if dx else 0.0
    half_dy = dy / 2.0 if dy else 0.0

    XX, YY = np.meshgrid(x_vals, y_vals)
    cell_polys = None
    use_polys = dx > 0 and dy > 0
    if use_polys:
        cell_polys = [
            [
                Polygon(
                    [
                        (xc - half_dx, yc - half_dy),
                        (xc + half_dx, yc - half_dy),
                        (xc + half_dx, yc + half_dy),
                        (xc - half_dx, yc + half_dy),
                    ]
                )
                for xc in x_vals
            ]
            for yc in y_vals
        ]

    values_inside: list[np.ndarray] = []
    values_outside: list[np.ndarray] = []
    per_day_mean: dict[pd.Timestamp, float] = {}

    for idx, t_val in enumerate(dates_clim):
        eg_mask = event_gdf[event_gdf["date_norm"] <= t_val]
        if eg_mask.empty:
            continue
        latest = eg_mask.sort_values("date_norm").iloc[-1]
        poly = _largest_polygon(latest.geometry)
        if poly is None:
            continue

        if fast:
            try:
                import rasterio.features
                from affine import Affine

                transform = Affine.translation(x_vals.min() - dx / 2.0, y_vals.min() - dy / 2.0) * Affine.scale(dx or 1.0, dy or 1.0)
                mask = rasterio.features.rasterize(
                    [(poly, 1)],
                    out_shape=(ny, nx),
                    transform=transform,
                    fill=0,
                    dtype="uint8",
                    all_touched=True,
                ).astype(bool)
            except Exception:
                mask = None
        else:
            mask = None

        if mask is None:
            poly_prep = prep(poly)
            if use_polys and cell_polys is not None:
                mask = np.zeros((ny, nx), dtype=bool)
                for iy in range(ny):
                    for ix in range(nx):
                        mask[iy, ix] = poly_prep.covers(cell_polys[iy][ix])
                if not mask.any():
                    pts = [Point(xc, yc) for xc, yc in zip(XX.ravel(), YY.ravel())]
                    inside = np.array([poly_prep.covers(p) for p in pts])
                    mask = inside.reshape((ny, nx))
            else:
                pts = [Point(xc, yc) for xc, yc in zip(XX.ravel(), YY.ravel())]
                inside = np.array([poly_prep.covers(p) for p in pts])
                mask = inside.reshape((ny, nx))

        da_slice = da.isel(time=idx)
        vals = da_slice.values
        vals_inside = vals[mask]
        vals_outside = vals[~mask]

        per_day_mean[t_val] = float(np.nanmean(vals_inside)) if vals_inside.size else np.nan
        values_inside.append(vals_inside.ravel())
        values_outside.append(vals_outside.ravel())

    values_inside_flat = np.concatenate(values_inside) if values_inside else np.array([])
    values_outside_flat = np.concatenate(values_outside) if values_outside else np.array([])

    return HullClimateSummary(
        values_inside=values_inside_flat,
        values_outside=values_outside_flat,
        per_day_mean=pd.Series(per_day_mean),
    )


def time_hull_to_vase(hull: TimeHull) -> Vase:
    """
    Convert a :class:`TimeHull` into a minimal vase representation.

    Parameters
    ----------
    hull
        Hull mesh produced by :func:`compute_time_hull_geometry`.

    Returns
    -------
    Vase
        Lightweight container with vertices, triangles, and metadata for
        visualization utilities.

    Notes
    -----
    This helper performs no computation beyond copying arrays into the
    vase structure so it is safe to call in lazy plotting pipelines.

    Examples
    --------
    >>> vase = time_hull_to_vase(hull)
    >>> sorted(vase.metadata.keys())
    ['event_id', 'metrics', 't_days_vert', 't_norm_vert']
    """

    return Vase(
        verts_km=hull.verts_km,
        tris=hull.tris,
        metadata={
            "metrics": hull.metrics,
            "event_id": hull.event.event_id,
            "t_days_vert": hull.t_days_vert,
            "t_norm_vert": hull.t_norm_vert,
        },
    )


def _gridmet_urls_for_var_years(variable: str, years: Iterable[int]) -> List[str]:
    return [f"https://www.northwestknowledge.net/metdata/data/{variable}_{y}.nc" for y in years]


def _download_gridmet_files_to_cache(urls: Sequence[str], cache_dir: Path) -> List[Path]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    for url in urls:
        fname = cache_dir / Path(url).name
        if not fname.exists():
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            fname.write_bytes(resp.content)
        paths.append(fname)
    return paths


def _load_real_gridmet_cube(
    lat: float,
    lon: float,
    start: pd.Timestamp,
    end: pd.Timestamp,
    *,
    variable: str = "tmmx",
    cache_dir: str | Path | None = None,
) -> xr.DataArray:
    cache_dir = Path(cache_dir or Path.home() / ".cache" / "cubedynamics" / "gridmet")
    years = range(start.year, end.year + 1)
    urls = _gridmet_urls_for_var_years(variable, years)
    paths = _download_gridmet_files_to_cache(urls, cache_dir)

    ds = xr.open_mfdataset([str(p) for p in paths], combine="by_coords")
    if "day" in ds.dims:
        ds = ds.rename({"day": "time"})
    ds = ds.sel(time=slice(start, end))

    # nearest grid point
    y_name = "lat" if "lat" in ds.coords else "y"
    x_name = "lon" if "lon" in ds.coords else "x"
    target_var = variable
    if target_var not in ds.data_vars and len(ds.data_vars) == 1:
        target_var = next(iter(ds.data_vars))
    da = ds[target_var].sel({y_name: lat, x_name: lon}, method="nearest")
    da.name = variable
    da = da.assign_coords({"lat": da[y_name], "lon": da[x_name]})
    da = da.drop_vars([c for c in [y_name, x_name] if c in da.coords and c not in ["lat", "lon"]])
    da = da.expand_dims({"y": [float(da.lat.values)], "x": [float(da.lon.values)]})
    da = da.transpose("time", "y", "x")
    da = da.assign_attrs({"gridmet_source": "real"})
    return da


def _load_synthetic_gridmet_cube(
    lat: float,
    lon: float,
    start: pd.Timestamp,
    end: pd.Timestamp,
    *,
    variable: str = "tmmx",
) -> xr.DataArray:
    times = pd.date_range(start, end, freq="D")
    y = np.linspace(lat - 0.1, lat + 0.1, 5)
    x = np.linspace(lon - 0.1, lon + 0.1, 5)
    rng = np.random.default_rng(42)
    data = rng.normal(loc=0.0, scale=1.0, size=(len(times), len(y), len(x)))
    da = xr.DataArray(
        data,
        coords={"time": times, "y": y, "x": x},
        dims=("time", "y", "x"),
        name=variable,
        attrs={"gridmet_source": "synthetic"},
    )
    return da


def load_gridmet_cube(
    lat: float,
    lon: float,
    start: pd.Timestamp,
    end: pd.Timestamp,
    *,
    variable: str = "tmmx",
    prefer_synthetic: bool = False,
    cache_dir: str | Path | None = None,
) -> xr.DataArray:
    if prefer_synthetic:
        return _load_synthetic_gridmet_cube(lat, lon, start, end, variable=variable)

    try:
        return _load_real_gridmet_cube(lat, lon, start, end, variable=variable, cache_dir=cache_dir)
    except Exception:
        return _load_synthetic_gridmet_cube(lat, lon, start, end, variable=variable)


def load_climate_cube_for_event(
    event: FireEventDaily,
    *,
    time_buffer_days: int = 14,
    variable: str = "tmmx",
    prefer_synthetic: bool = False,
    freq: str | None = None,
    prefer_streaming: bool = True,
    allow_synthetic: bool = False,
    verbose: bool = False,
) -> ClimateCube:
    from cubedynamics.data import gridmet as gridmet_loader
    from cubedynamics.data import prism as prism_loader

    start = event.t0 - pd.Timedelta(days=time_buffer_days)
    end = event.t1 + pd.Timedelta(days=time_buffer_days)
    var_lower = variable.lower()
    allow_synth = allow_synthetic or prefer_synthetic

    gridmet_vars = {
        "vpd",
        "tmmx",
        "tmmn",
        "rmax",
        "rmin",
        "etr",
        "pr",
        "erc",
        "fm100",
        "fm1000",
        "pdsi",
        "pet",
        "srad",
        "bi",
    }
    sentinel_vars = {"ndvi", "ndvi_zscore"}
    prism_vars = {"ppt", "tmin", "tmax", "tmean"}

    freq_use = freq
    ds = None
    source = "gridmet"
    if var_lower in prism_vars:
        freq_use = freq or "D"
        source = "prism"
        ds = prism_loader.load_prism_cube(
            lat=event.centroid_lat,
            lon=event.centroid_lon,
            start=start,
            end=end,
            variable=variable,
            freq=freq_use,
            prefer_streaming=prefer_streaming,
            show_progress=verbose,
            allow_synthetic=allow_synth,
        )
    elif var_lower in sentinel_vars:
        raise RuntimeError(
            "Sentinel-2 NDVI variables must be provided as cubes (cube-first fire_plot) or via the sentinel loaders;"
            " no implicit download is attempted."
        )
    else:
        freq_use = freq or "D"
        ds = gridmet_loader.load_gridmet_cube(
            lat=event.centroid_lat,
            lon=event.centroid_lon,
            start=start,
            end=end,
            variable=variable,
            freq=freq_use,
            prefer_streaming=prefer_streaming,
            show_progress=verbose,
            allow_synthetic=allow_synth,
        )

    if isinstance(ds, xr.DataArray):
        cube_da = ds
    else:
        target_var = variable if variable in ds.data_vars else next(iter(ds.data_vars))
        cube_da = ds[target_var]
        cube_da.attrs.update(ds.attrs)
    log(verbose, f"{source.upper()} source: {cube_da.attrs.get('source')}")
    return ClimateCube(da=cube_da)


def infer_spatial_dims(da: xr.DataArray) -> Tuple[str, str]:
    if "y" in da.dims and "x" in da.dims:
        return "y", "x"
    if "lat" in da.dims and "lon" in da.dims:
        return "lat", "lon"
    raise ValueError(f"Cannot infer spatial dims from {da.dims}")


def infer_epsg(da: xr.DataArray) -> Optional[int]:
    epsg = None
    if "epsg" in da.attrs:
        try:
            epsg = int(da.attrs["epsg"])
        except Exception:
            epsg = None

    if epsg is None and "epsg" in da.coords:
        try:
            coord = da["epsg"]
            if coord.ndim == 0:
                epsg = int(coord.values)
        except Exception:
            epsg = None

    if epsg is None and hasattr(da, "rio"):
        try:
            crs = da.rio.crs
            if crs is not None:
                epsg = crs.to_epsg()
        except Exception:
            epsg = None

    if epsg is None and "crs" in da.attrs:
        try:
            import pyproj

            crs = pyproj.CRS.from_user_input(da.attrs["crs"])
            epsg = crs.to_epsg()
        except Exception:
            epsg = None

    if epsg is None:
        try:
            y_dim, x_dim = infer_spatial_dims(da)
        except Exception:
            y_dim, x_dim = None, None

        if y_dim == "lat" and x_dim == "lon":
            epsg = 4326
        elif y_dim == "y" and x_dim == "x":
            x_vals = np.asarray(da[x_dim].values)
            y_vals = np.asarray(da[y_dim].values)
            if np.nanmax(np.abs(x_vals)) <= 180 and np.nanmax(np.abs(y_vals)) <= 90:
                epsg = 4326

    if epsg is None:
        raise ValueError("Could not infer EPSG; add attrs['epsg'] or coordinate metadata")

    return epsg


def build_inside_outside_climate_samples(
    event: FireEventDaily,
    cube: ClimateCube,
    *,
    date_col: str = "date",
    verbose: bool = False,
) -> HullClimateSummary:
    da = cube.da if hasattr(cube, "da") else cube
    time_vals = normalize_dates(da["time"].values)
    mask_time = (time_vals >= event.t0) & (time_vals <= event.t1)
    if not mask_time.any():
        raise ValueError("Climate cube has no timesteps overlapping the fire time window.")

    da_evt = da.isel(time=np.where(mask_time)[0])
    return sample_inside_outside(event, da_evt, date_col=date_col, fast=False, verbose=verbose)


def _infer_vertex_slice_index(hull: FireHull) -> tuple[np.ndarray, np.ndarray]:
    """Return sorted unique layer days and the per-vertex slice index.

    This is the canonical geometry/time mapping used by both diagnostics and
    environmental projection. It ensures scalar values are attached using the
    hull's explicit time coordinates rather than assuming a particular vertex
    block layout.
    """

    t_days_vert = np.asarray(hull.t_days_vert, dtype=float)
    if t_days_vert.shape[0] != np.asarray(hull.verts_km).shape[0]:
        raise ValueError(
            "Per-vertex time coordinate mismatch: "
            f"{t_days_vert.shape[0]} t_days values for {np.asarray(hull.verts_km).shape[0]} vertices."
        )
    return np.unique(t_days_vert, return_inverse=True)


def _summary_to_vertex_values(
    hull: FireHull,
    summary: HullClimateSummary,
) -> tuple[pd.DatetimeIndex, np.ndarray, np.ndarray, np.ndarray]:
    """Project per-day climate summary values onto explicit hull vertices."""

    layer_days, vertex_slice_index = _infer_vertex_slice_index(hull)
    per_day = summary.per_day_mean.copy()
    per_day.index = normalize_dates(per_day.index)
    per_day = per_day.sort_index()

    layer_dates = normalize_dates(
        hull.event.t0 + pd.to_timedelta(layer_days - np.nanmin(layer_days), unit="D")
    )
    layer_vals = per_day.reindex(layer_dates)
    if layer_vals.isna().any():
        layer_vals = layer_vals.ffill().bfill()
    layer_values = np.asarray(layer_vals.values, dtype=float)
    vertex_values = layer_values[vertex_slice_index]
    return layer_dates, layer_values, vertex_values, vertex_slice_index.astype(int)


def plot_climate_filled_hull(
    hull: TimeHull,
    summary: HullClimateSummary,
    *,
    values: np.ndarray | None = None,
    title_prefix: str = "GRIDMET",
    var_label: str = "value",
    save_prefix: Optional[str] = None,
    color_limits: Optional[Tuple[float, float]] = None,
    z_exaggeration: float = 2.2,
    scalar_debug_mode: Optional[str] = None,
    debug: bool = False,
) -> go.Figure:
    def _sanitize_mesh_inputs(
        verts_in: np.ndarray,
        tris_in: np.ndarray,
        t_days_in: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        verts_arr = np.asarray(verts_in, dtype=float)
        tris_arr = np.asarray(tris_in, dtype=int)
        t_days_arr = np.asarray(t_days_in, dtype=float)

        if verts_arr.ndim != 2 or verts_arr.shape[1] != 3:
            raise ValueError("TimeHull verts_km must have shape (N, 3).")
        if tris_arr.ndim != 2 or tris_arr.shape[1] != 3:
            raise ValueError("TimeHull tris must have shape (M, 3).")
        if t_days_arr.shape[0] != verts_arr.shape[0]:
            raise ValueError(
                "Per-vertex time coordinate mismatch: "
                f"{t_days_arr.shape[0]} t_days values for {verts_arr.shape[0]} vertices."
            )

        valid_vertex_mask = np.isfinite(verts_arr).all(axis=1) & np.isfinite(t_days_arr)
        if not np.all(valid_vertex_mask):
            old_to_new = np.full(verts_arr.shape[0], -1, dtype=int)
            old_to_new[valid_vertex_mask] = np.arange(int(valid_vertex_mask.sum()))
            verts_arr = verts_arr[valid_vertex_mask]
            t_days_arr = t_days_arr[valid_vertex_mask]
            remapped = old_to_new[tris_arr]
            tri_valid = (remapped >= 0).all(axis=1)
            tris_arr = remapped[tri_valid]

        if verts_arr.shape[0] == 0:
            raise ValueError("TimeHull contains no finite vertices to render.")
        if tris_arr.shape[0] == 0:
            raise ValueError("TimeHull contains no valid triangles to render.")

        tri_bounds_ok = (tris_arr >= 0).all() and (tris_arr < verts_arr.shape[0]).all()
        if not tri_bounds_ok:
            tri_valid = ((tris_arr >= 0) & (tris_arr < verts_arr.shape[0])).all(axis=1)
            tris_arr = tris_arr[tri_valid]
        if tris_arr.shape[0] == 0:
            raise ValueError("TimeHull contains no in-bounds triangles to render.")

        return verts_arr, tris_arr, t_days_arr, valid_vertex_mask

    def _build_vertex_slice_index() -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
        layer_days, vertex_slice_index = _infer_vertex_slice_index(
            FireHull(
                event=hull.event,
                verts_km=verts,
                tris=tris,
                t_days_vert=t_days_vert,
                t_norm_vert=np.asarray(hull.t_norm_vert, dtype=float)[: verts.shape[0]],
                metrics=HullMetrics(getattr(hull, "metrics", {})),
            )
        )
        n_layers_local = int(layer_days.size)
        if n_layers_local <= 0:
            raise ValueError("TimeHull has no time layers to color.")

        verts_z = np.asarray(verts[:, 2], dtype=float)
        z_matches_t = bool(np.allclose(verts_z, t_days_vert, equal_nan=True))
        for layer_idx, layer_day in enumerate(layer_days):
            layer_mask = vertex_slice_index == layer_idx
            if not np.any(layer_mask):
                continue
            layer_z = verts_z[layer_mask]
            if not np.allclose(layer_z, layer_day, equal_nan=True):
                raise ValueError(
                    "Vertex/time ordering mismatch: hull z coordinates do not match "
                    f"slice {layer_idx} (expected day {layer_day})."
                )

        tri_slice_index = vertex_slice_index[tris]
        tri_slice_min = tri_slice_index.min(axis=1)
        tri_slice_max = tri_slice_index.max(axis=1)
        tri_slice_span = tri_slice_max - tri_slice_min
        if np.any(tri_slice_span > 1):
            raise ValueError(
                "Triangle/time ordering mismatch: found triangles spanning more than "
                "adjacent time slices."
            )

        alignment = {
            "vertex_alignment": {
                "mode": "vertex",
                "len_values": int(vertex_slice_index.shape[0]),
                "len_verts": int(verts.shape[0]),
                "z_matches_t_days": z_matches_t,
                "n_layers": n_layers_local,
                "approx_unique_slices": int(np.unique(vertex_slice_index).size),
            },
            "face_alignment": {
                "mode": "vertex_colors_on_faces",
                "len_values": int(tri_slice_min.shape[0]),
                "len_tris": int(tris.shape[0]),
                "min_slice_span": int(tri_slice_span.min()) if tri_slice_span.size else 0,
                "max_slice_span": int(tri_slice_span.max()) if tri_slice_span.size else 0,
            },
        }
        return layer_days, vertex_slice_index.astype(int), alignment

    def _scalar_stats(values: np.ndarray) -> dict[str, Any]:
        values = np.asarray(values)
        finite = values[np.isfinite(values)]
        pct = [1, 5, 25, 50, 75, 95, 99]
        return {
            "shape": tuple(values.shape),
            "dtype": str(values.dtype),
            "nan_count": int(np.isnan(values).sum()),
            "min": float(np.nanmin(finite)) if finite.size else float("nan"),
            "max": float(np.nanmax(finite)) if finite.size else float("nan"),
            "percentiles": dict(
                zip(
                    [str(p) for p in pct],
                    np.nanpercentile(finite, pct).tolist() if finite.size else [float("nan")] * len(pct),
                )
            ),
            "approx_unique_count": int(np.unique(finite).size),
        }

    verts, tris, t_days_vert, valid_vertex_mask = _sanitize_mesh_inputs(hull.verts_km, hull.tris, hull.t_days_vert)
    n_vertices = int(verts.shape[0])
    layer_days, vertex_slice_index, alignment = _build_vertex_slice_index()
    n_layers = int(layer_days.size)

    # Scalar values are colored per-vertex. We build an explicit
    # vertex -> slice -> climate-value mapping from hull.t_days_vert so mesh
    # colors stay aligned even if vertex ordering changes during mesh assembly.
    intensities = np.asarray(values, dtype=float)[valid_vertex_mask] if values is not None else None
    if intensities is None and isinstance(summary, HullClimateSummary) and summary.per_day_mean.size:
        per_day = summary.per_day_mean.copy()
        per_day.index = normalize_dates(per_day.index)
        per_day = per_day.sort_index()
        layer_date_index = normalize_dates(
            hull.event.t0 + pd.to_timedelta(layer_days - np.nanmin(layer_days), unit="D")
        )
        layer_vals = per_day.reindex(layer_date_index)
        if layer_vals.isna().any():
            layer_vals = layer_vals.ffill().bfill()
        day_vals = np.asarray(layer_vals.values, dtype=float)
        intensities = day_vals[vertex_slice_index]
    if intensities is not None and intensities.shape[0] != n_vertices:
        raise ValueError(
            "Hull climate scalar/vertex mismatch: "
            f"{intensities.shape[0]} intensities for {n_vertices} vertices."
        )

    # Developer diagnostic mode: color by z/time to confirm vertical banding.
    if scalar_debug_mode == "z":
        intensities = verts[:, 2].astype(float)
    elif scalar_debug_mode == "slice":
        # Diagnostic mode to verify explicit slice->vertex alignment.
        intensities = vertex_slice_index.astype(float)

    if intensities is not None:
        finite = intensities[np.isfinite(intensities)]
        if color_limits is None and finite.size:
            # Display-only robust normalization to preserve visible scalar bands.
            cmin = float(np.nanpercentile(finite, 2))
            cmax = float(np.nanpercentile(finite, 98))
            if not np.isfinite(cmin) or not np.isfinite(cmax) or cmax <= cmin:
                cmin = float(np.nanmin(finite))
                cmax = float(np.nanmax(finite))
                if cmax <= cmin:
                    cmax = cmin + 1e-9
            color_limits = (cmin, cmax)
        if debug:
            print(
                "fire_hull_scalar_debug:",
                {
                    "verts_shape": tuple(verts.shape),
                    "tris_shape": tuple(tris.shape),
                    "scalar_stats": _scalar_stats(intensities),
                    "mode": scalar_debug_mode or "climate",
                    "n_layers": n_layers,
                    **alignment,
                },
            )

    fig = go.Figure(
        data=[
            go.Mesh3d(
                x=verts[:, 0],
                y=verts[:, 1],
                z=verts[:, 2],
                i=tris[:, 0],
                j=tris[:, 1],
                k=tris[:, 2],
                intensity=intensities,
                colorscale="Viridis",
                intensitymode="vertex",
                flatshading=False,
                showscale=True,
                cmin=None if color_limits is None else color_limits[0],
                cmax=None if color_limits is None else color_limits[1],
                colorbar=dict(title=var_label),
                opacity=0.8,
            )
        ],
    )

    fig.update_layout(
        title=f"{title_prefix}: {var_label}",
        scene=dict(
            xaxis_title="x (km)",
            yaxis_title="y (km)",
            zaxis_title="time (days)",
            aspectmode="manual",
            aspectratio=dict(x=1.0, y=1.0, z=float(max(0.1, z_exaggeration))),
            xaxis=dict(showbackground=False, showgrid=False, zeroline=False),
            yaxis=dict(showbackground=False, showgrid=False, zeroline=False),
            zaxis=dict(showbackground=False, showgrid=False, zeroline=False),
        ),
        template="plotly_white",
    )

    if save_prefix:
        try:
            fig.write_image(f"{save_prefix}.png")
        except Exception:
            pass

    return fig


def plot_inside_outside_hist(
    summary: HullClimateSummary,
    *,
    bins: int = 40,
    var_label: str = "value",
):
    import matplotlib.pyplot as plt

    inside = np.asarray(summary.values_inside).ravel()
    outside = np.asarray(summary.values_outside).ravel()

    plt.figure(figsize=(5, 3))
    if inside.size:
        plt.hist(
            inside,
            bins=bins,
            alpha=0.6,
            density=True,
            label="inside",
            histtype="stepfilled",
        )
    if outside.size:
        plt.hist(
            outside,
            bins=bins,
            alpha=0.6,
            density=True,
            label="outside",
            histtype="step",
        )

    plt.xlabel(var_label)
    plt.ylabel("Density")
    plt.title(f"{var_label}: inside vs outside fire perimeters")
    plt.legend()
    plt.tight_layout()
    plt.show()


def _hull_grid(hull: TimeHull) -> tuple[np.ndarray, int, int]:
    """
    Recover the (M, T, 3) grid from a TimeHull, where:
      M = number of days (layers)
      T = number of angular samples per layer

    Assumes verts_km are laid out as consecutive "rings" over time,
    as produced by compute_time_hull_geometry.
    """
    verts = hull.verts_km  # shape (M*T, 3)
    days = int(round(hull.metrics.get("days", 0)))
    if days <= 0:
        raise ValueError("Hull has non-positive 'days' metric; cannot reshape.")

    n_verts = verts.shape[0]
    if n_verts % days != 0:
        raise ValueError(
            f"Cannot reshape verts into (days, T, 3): "
            f"{n_verts} vertices not divisible by days={days}"
        )

    T = n_verts // days
    P = verts.reshape(days, T, 3)
    return P, days, T


def compute_derivative_hull(
    hull: TimeHull,
    *,
    order: int = 1,
    eps: float = 1e-6,
) -> TimeHull:
    """
    Build a derivative-based hull from an existing TimeHull.

    Parameters
    ----------
    hull
        Base TimeHull in km,km,days from compute_time_hull_geometry.
    order
        1 → derivative hull encodes perimeter *speed* (km/day).
        2 → derivative hull encodes perimeter *acceleration* (km/day²).
    eps
        Small tolerance to avoid division by zero when normalizing.

    Returns
    -------
    TimeHull
        A new hull with the same topology (tris) and time coordinates,
        but with radius at each (day, theta) proportional to speed or
        acceleration, respectively.
    """
    if order not in (1, 2):
        raise ValueError("order must be 1 or 2")

    P, M, T = _hull_grid(hull)      # (M, T, 3)
    xy = P[..., :2]                 # (M, T, 2), km coordinates

    # First derivative of perimeter position in time: km/day
    dxy_dt = np.gradient(xy, axis=0)  # central differences along time axis
    speed = np.linalg.norm(dxy_dt, axis=-1)  # (M, T), km/day

    if order == 1:
        field = speed
        field_name = "speed_km_per_day"
    else:
        # Second derivative of spread speed: km/day²
        accel = np.gradient(speed, axis=0)
        field = accel
        field_name = "accel_km_per_day2"

    # Use derivative magnitude as new radius, preserving angular direction
    r_orig = np.linalg.norm(xy, axis=-1)  # (M, T)
    U = np.zeros_like(xy)                 # unit directions (M, T, 2)

    mask = r_orig > eps
    U[mask] = xy[mask] / r_orig[mask][..., None]
    U[~mask] = np.array([1.0, 0.0])  # arbitrary direction for degenerate centers

    R_new = np.abs(field)  # radius encodes magnitude of derivative field

    P_new = np.zeros_like(P)
    P_new[..., :2] = R_new[..., None] * U
    P_new[..., 2]  = P[..., 2]  # keep same time (days)

    verts_new = P_new.reshape(-1, 3)

    rmax = float(np.nanmax(R_new)) if np.isfinite(R_new).any() else 0.0
    metrics = {
        "scale_km": rmax,
        "days": float(M),
        "volume_km2_days": np.nan,   # not meaningful for derivatives
        "surface_km_day": np.nan,    # not meaningful for derivatives
        "field_name": field_name,
    }

    return FireHull(
        event=hull.event,
        verts_km=verts_new,
        tris=hull.tris,
        t_days_vert=hull.t_days_vert,
        t_norm_vert=hull.t_norm_vert,
        metrics=HullMetrics(metrics),
    )


def plot_derivative_hull(
    base_hull: TimeHull,
    deriv_hull: TimeHull,
    *,
    order: int = 1,
    title_prefix: str = "Fire derivative hull",
) -> go.Figure:
    """
    Plot a derivative hull with color and radius encoding the same
    derivative quantity (speed or acceleration).

    base_hull is used to recompute the underlying derivative field
    (speed or acceleration) so that intensity and geometry agree.
    """
    P, M, T = _hull_grid(base_hull)
    xy = P[..., :2]

    # First derivative: km/day
    dxy_dt = np.gradient(xy, axis=0)
    speed = np.linalg.norm(dxy_dt, axis=-1)  # (M, T)

    if order == 1:
        field = speed
        var_label = "Perimeter speed (km/day)"
    else:
        accel = np.gradient(speed, axis=0)
        field = accel
        var_label = "Perimeter acceleration (km/day²)"

    intensities = np.abs(field).ravel()

    verts = deriv_hull.verts_km
    tris  = deriv_hull.tris
    x, y, z = verts[:, 0], verts[:, 1], verts[:, 2]
    i, j, k = tris.T

    if np.isfinite(intensities).any():
        vmin = float(np.nanpercentile(intensities, 5))
        vmax = float(np.nanpercentile(intensities, 95))
    else:
        vmin, vmax = 0.0, 1.0

    mesh = go.Mesh3d(
        x=x,
        y=y,
        z=z,
        i=i,
        j=j,
        k=k,
        intensity=intensities,
        colorscale="Viridis",
        cmin=vmin,
        cmax=vmax,
        opacity=0.8,
        flatshading=True,
        colorbar=dict(title=var_label),
        name="Derivative hull",
    )

    title = (
        f"{title_prefix} – Event {base_hull.event.event_id} "
        f"| order={order}"
    )

    fig = go.Figure(data=[mesh])
    fig.update_layout(
        title=title,
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            aspectmode="data",
        ),
        margin=dict(l=0, r=0, t=60, b=0),
        showlegend=False,
    )
    return fig


__all__ = [
    "TemporalSupport",
    "GRIDMET_SUPPORT",
    "FireEventDaily",
    "FireHull",
    "TimeHull",
    "ClimateCube",
    "HullClimateSummary",
    "HullMetrics",
    "HullEnvironmentField",
    "load_fired_conus_ak",
    "pick_event_with_joint_support",
    "build_fire_event_daily",
    "build_fire_event",
    "compute_time_hull_geometry",
    "sample_inside_outside",
    "build_inside_outside_climate_samples",
    "time_hull_to_vase",
    "load_climate_cube_for_event",
    "plot_climate_filled_hull",
    "plot_inside_outside_hist",
    "compute_derivative_hull",
    "plot_derivative_hull",
]
