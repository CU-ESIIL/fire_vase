"""Run one real FIRED event through a real gridMET fire-vase smoke test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    import geopandas as gpd
    from cubedynamics.fire_time_hull import FireEventDaily


FireEventDaily = None
load_fired_conus_ak = None
stream_gridmet_to_cube = None
fire_verbs = None


WEST_BBOX = (-125.0, 31.0, -102.0, 49.5)
PRESCRIBED_PATTERN = re.compile(r"prescrib|\\brx\\b|planned|broadcast|pile", re.I)


def _ensure_runtime_deps() -> None:
    global FireEventDaily, fire_verbs, load_fired_conus_ak, stream_gridmet_to_cube

    if FireEventDaily is None or load_fired_conus_ak is None:
        from cubedynamics.fire_time_hull import FireEventDaily as _FireEventDaily
        from cubedynamics.fire_time_hull import load_fired_conus_ak as _load_fired_conus_ak

        FireEventDaily = FireEventDaily or _FireEventDaily
        load_fired_conus_ak = load_fired_conus_ak or _load_fired_conus_ak
    if stream_gridmet_to_cube is None:
        from cubedynamics.streaming.gridmet import stream_gridmet_to_cube as _stream_gridmet_to_cube

        stream_gridmet_to_cube = _stream_gridmet_to_cube
    if fire_verbs is None:
        from cubedynamics.verbs import fire as _fire_verbs

        fire_verbs = _fire_verbs


def _choose_column(gdf: gpd.GeoDataFrame, candidates: tuple[str, ...]) -> str:
    lower = {name.lower(): name for name in gdf.columns}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    raise ValueError(f"Could not find any of columns {candidates!r}")


def _western_ids(fired_daily: gpd.GeoDataFrame, id_col: str) -> set[Any]:
    from shapely.geometry import box

    min_lon, min_lat, max_lon, max_lat = WEST_BBOX
    candidates = fired_daily[[id_col, "geometry"]].copy()
    candidates = candidates[candidates.geometry.notna()]
    if candidates.crs is not None and candidates.crs.to_epsg() != 4326:
        candidates = candidates.to_crs(4326)
    west_box = box(min_lon, min_lat, max_lon, max_lat)
    west = candidates[candidates.geometry.intersects(west_box)]
    return set(west[id_col].dropna().unique())


def _prescribed_ids(events: gpd.GeoDataFrame, id_col: str) -> tuple[set[Any], dict[str, list[str]]]:
    inspected: dict[str, list[str]] = {}
    hits: set[Any] = set()
    for column in events.columns:
        if column == "geometry":
            continue
        values = events[column]
        if not (
            pd.api.types.is_object_dtype(values)
            or pd.api.types.is_string_dtype(values)
            or isinstance(values.dtype, pd.CategoricalDtype)
        ):
            continue
        as_text = values.astype(str)
        matching = sorted({value for value in as_text.dropna().unique() if PRESCRIBED_PATTERN.search(value)})
        if matching:
            inspected[column] = matching[:20]
            hits.update(events.loc[as_text.str.contains(PRESCRIBED_PATTERN, na=False), id_col].dropna().unique())
    return hits, inspected


def _event_summary_table(fired_daily: gpd.GeoDataFrame, id_col: str, date_col: str) -> pd.DataFrame:
    rows = []
    for event_id, group in fired_daily.groupby(id_col):
        dates = pd.to_datetime(group[date_col], errors="coerce")
        dates = dates.dropna()
        if dates.empty:
            continue
        rows.append(
            {
                "event_id": event_id,
                "start": dates.min(),
                "end": dates.max(),
                "duration_days": int((dates.max().normalize() - dates.min().normalize()).days) + 1,
                "daily_rows": int(len(group)),
            }
        )
    return pd.DataFrame(rows)


def _event_geojson(event: FireEventDaily, buffer_degrees: float = 0.08) -> dict[str, Any]:
    geom = event.gdf.geometry.union_all() if hasattr(event.gdf.geometry, "union_all") else event.gdf.geometry.unary_union
    minx, miny, maxx, maxy = geom.bounds
    minx -= buffer_degrees
    miny -= buffer_degrees
    maxx += buffer_degrees
    maxy += buffer_degrees
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [minx, miny],
                    [minx, maxy],
                    [maxx, maxy],
                    [maxx, miny],
                    [minx, miny],
                ]
            ],
        },
        "properties": {"event_id": str(event.event_id)},
    }


def _layer_values_from_summary(results: dict[str, Any], layer_days: np.ndarray) -> np.ndarray | None:
    summary = results.get("summary")
    per_day_mean = getattr(summary, "per_day_mean", None)
    if per_day_mean is None or len(per_day_mean) == 0:
        return None

    event = results["event"]
    per_day = per_day_mean.copy()
    per_day.index = pd.to_datetime(per_day.index).normalize()
    per_day = per_day.sort_index()
    layer_dates = pd.to_datetime(event.t0 + pd.to_timedelta(layer_days - np.nanmin(layer_days), unit="D")).normalize()
    layer_values = per_day.reindex(layer_dates)
    if layer_values.isna().any():
        layer_values = layer_values.ffill().bfill()
    return np.asarray(layer_values.values, dtype=float)


def _static_face_values_by_day(results: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return mesh faces and one climate scalar per daily face band.

    Matplotlib's Poly3DCollection only accepts face colors. Averaging the three
    vertex values creates two different colors for the two triangles that make
    up a single side-wall day band. Instead, assign each face to an explicit
    hull time layer so the PNG represents daily climate bands, not tessellation.
    """

    hull = results["hull"]
    mesh = results["fig_hull"].data[0]
    verts = np.asarray(hull.verts_km, dtype=float)
    tris = np.asarray(hull.tris, dtype=int)
    faces = verts[tris]

    layer_days, vertex_layer = np.unique(np.asarray(hull.t_days_vert, dtype=float), return_inverse=True)
    layer_values = _layer_values_from_summary(results, layer_days)
    if layer_values is None:
        intensities = np.asarray(getattr(mesh, "intensity", np.asarray(hull.t_days_vert)), dtype=float)
        layer_values = np.array(
            [
                float(np.nanmedian(intensities[vertex_layer == layer_idx]))
                for layer_idx in range(layer_days.size)
            ],
            dtype=float,
        )

    tri_layers = vertex_layer[tris]
    face_layers = tri_layers.min(axis=1)
    tri_values = layer_values[face_layers]
    return verts, faces, tri_values


def _save_static_hull_png(results: dict[str, Any], output_path: Path) -> None:
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    verts, faces, tri_values = _static_face_values_by_day(results)
    finite = tri_values[np.isfinite(tri_values)]
    if finite.size:
        vmin, vmax = float(np.nanpercentile(finite, 2)), float(np.nanpercentile(finite, 98))
        if vmax <= vmin:
            vmax = vmin + 1e-9
    else:
        vmin, vmax = 0.0, 1.0
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    colors = plt.cm.viridis(norm(tri_values))

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111, projection="3d")
    poly = Poly3DCollection(faces, facecolors=colors, edgecolors="none", linewidths=0.0, alpha=0.88)
    ax.add_collection3d(poly)
    ax.auto_scale_xyz(verts[:, 0], verts[:, 1], verts[:, 2])
    ax.set_xlabel("x (km)")
    ax.set_ylabel("y (km)")
    ax.set_zlabel("time (days)")
    ax.view_init(elev=24, azim=-55)
    ax.set_title(f"FIRED event {results['event'].event_id}: gridMET tmmx fire vase")
    mappable = plt.cm.ScalarMappable(norm=norm, cmap="viridis")
    mappable.set_array([])
    fig.colorbar(mappable, ax=ax, shrink=0.7, label="Max temperature (K)")
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def _diagnostic_gridmet_dataset(
    *,
    event,
    start: str,
    end: str,
    primary_variable: str,
    primary_cube,
    variables: list[str] | None,
):
    if not variables:
        return primary_cube

    import xarray as xr

    arrays = {}
    for name in dict.fromkeys(variables):
        if name == primary_variable:
            cube = primary_cube
        else:
            cube = stream_gridmet_to_cube(
                aoi_geojson=_event_geojson(event),
                variable=name,
                start=start,
                end=end,
                chunks={"time": 16},
                show_progress=False,
            )
            cube = cube.assign_attrs({"epsg": 4326, "source": "gridmet_real_yearly_http_stream"})
        arrays[name] = cube.rename(name)
    return xr.Dataset(arrays)


def _save_diagnostic_panel(results: dict[str, Any], output_path: Path) -> None:
    from cubedynamics import verbs as v

    fig = v.diagnostic_panel(
        results,
        output_path=output_path,
        title=f"FIRED event {results['event'].event_id}: fire VASE diagnostic panel",
    )
    try:
        import matplotlib.pyplot as plt

        plt.close(fig)
    except Exception:
        pass


def run(
    output_dir: Path,
    *,
    min_days: int,
    max_days: int,
    variable: str,
    diagnostic_variables: list[str] | None = None,
) -> dict[str, Any]:
    _ensure_runtime_deps()
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / "fired-cache"

    fired_daily = load_fired_conus_ak(which="daily", prefer="gpkg", cache_dir=cache_dir, download=True)
    fired_events = load_fired_conus_ak(which="events", prefer="gpkg", cache_dir=cache_dir, download=True)
    id_col = _choose_column(fired_daily, ("id", "event_id", "Event_ID", "fire_id"))
    date_col = _choose_column(fired_daily, ("date", "ig_date", "start_date", "Date"))
    event_id_col = _choose_column(fired_events, (id_col, "id", "event_id", "Event_ID", "fire_id"))

    west_ids = _western_ids(fired_daily, id_col)
    prescribed_ids, prescribed_evidence = _prescribed_ids(fired_events, event_id_col)
    candidates = west_ids & prescribed_ids if prescribed_ids else west_ids

    summary = _event_summary_table(fired_daily[fired_daily[id_col].isin(candidates)], id_col, date_col)
    summary = summary[(summary["duration_days"] >= min_days) & (summary["duration_days"] <= max_days)]
    if summary.empty:
        raise RuntimeError("No western FIRED event matched the requested duration and prescribed filters.")
    summary = summary.sort_values(["duration_days", "start"], ascending=[False, True]).reset_index(drop=True)
    selected_id = summary.loc[0, "event_id"]

    event = FireEventDaily.from_fired(fired_daily, selected_id, date_col=date_col)
    start = (event.t0 - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    end = (event.t1 + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    gridmet = stream_gridmet_to_cube(
        aoi_geojson=_event_geojson(event),
        variable=variable,
        start=start,
        end=end,
        chunks={"time": 16},
        show_progress=False,
    )
    gridmet = gridmet.assign_attrs({"epsg": 4326, "source": "gridmet_real_yearly_http_stream"})

    results = fire_verbs.fire_plot(
        gridmet,
        fired_event=event,
        climate_variable=variable,
        time_buffer_days=1,
        n_ring_samples=64,
        n_theta=96,
        fast=True,
        allow_synthetic=False,
        show_hist=False,
        verbose=False,
    )
    results["diagnostic_cube"] = _diagnostic_gridmet_dataset(
        event=event,
        start=start,
        end=end,
        primary_variable=variable,
        primary_cube=gridmet,
        variables=diagnostic_variables,
    )

    interactive_path = output_dir / "real_fire_vase_gridmet_interactive.html"
    static_path = output_dir / "real_fire_vase_gridmet_static.png"
    diagnostic_path = output_dir / "real_fire_vase_gridmet_diagnostic.png"
    results["fig_hull"].write_html(str(interactive_path), include_plotlyjs="cdn")
    _save_static_hull_png(results, static_path)
    _save_diagnostic_panel(results, diagnostic_path)

    manifest = {
        "event_id": str(event.event_id),
        "event_start": str(event.t0.date()),
        "event_end": str(event.t1.date()),
        "duration_days": event.duration_days,
        "centroid_lat": event.centroid_lat,
        "centroid_lon": event.centroid_lon,
        "western_bbox": WEST_BBOX,
        "prescribed_filter_available": bool(prescribed_ids),
        "prescribed_evidence": prescribed_evidence,
        "selected_from_prescribed_ids": bool(selected_id in prescribed_ids),
        "gridmet_variable": variable,
        "gridmet_shape": dict(gridmet.sizes),
        "hull_metrics": dict(results["hull"].metrics),
        "inside_samples": int(results["summary"].values_inside.size),
        "outside_samples": int(results["summary"].values_outside.size),
        "color_limits": [float(v) for v in results["color_limits"]],
        "interactive_html": str(interactive_path),
        "static_png": str(static_path),
        "diagnostic_png": str(diagnostic_path),
        "diagnostic_variables": list(diagnostic_variables or [variable]),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    summary.head(25).to_csv(output_dir / "candidate_events.csv", index=False)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/fire-vase-gridmet-real"))
    parser.add_argument("--min-days", type=int, default=3)
    parser.add_argument("--max-days", type=int, default=14)
    parser.add_argument("--variable", default="tmmx")
    parser.add_argument("--diagnostic-variables", nargs="*", default=None)
    args = parser.parse_args()
    manifest = run(
        args.output_dir,
        min_days=args.min_days,
        max_days=args.max_days,
        variable=args.variable,
        diagnostic_variables=args.diagnostic_variables,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
