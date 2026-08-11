"""Create a small prescribed-burn VASE panel for documentation.

This example is intentionally offline-friendly. It uses synthetic daily
perimeters and a synthetic climate cube, then runs the public
``v.fire_vase_panel`` verb exactly as a real FIRED/gridMET workflow would after
the data have been loaded.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.affinity import rotate, scale, translate
from shapely.geometry import box
from shapely.ops import unary_union
import xarray as xr

from cubedynamics import pipe, verbs as v


def _synthetic_fired() -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    starts = [
        (-122.20, 39.10),
        (-121.85, 39.18),
        (-122.05, 38.86),
        (-121.72, 38.96),
    ]
    rows = []
    event_rows = []
    for idx, (lon, lat) in enumerate(starts, start=101):
        daily_geoms = []
        start_date = pd.Timestamp("2020-08-01") + pd.Timedelta(days=idx - 101)
        for day in range(5):
            geom = box(lon, lat, lon + 0.055, lat + 0.045)
            geom = scale(geom, xfact=1.0 + 0.14 * day, yfact=1.0 + 0.10 * day, origin="center")
            geom = rotate(geom, angle=(idx * 9 + day * 7) % 35, origin="center")
            geom = translate(geom, xoff=0.012 * np.sin(day), yoff=0.008 * np.cos(day))
            daily_geoms.append(geom)
            rows.append(
                {
                    "id": idx,
                    "date": start_date + pd.Timedelta(days=day),
                    "geometry": geom,
                }
            )
        event_rows.append(
            {
                "id": idx,
                "fire_type": "prescribed burn",
                "geometry": unary_union(daily_geoms),
            }
        )

    return (
        gpd.GeoDataFrame(rows, crs="EPSG:4326"),
        gpd.GeoDataFrame(event_rows, crs="EPSG:4326"),
    )


def _synthetic_climate_cube() -> xr.DataArray:
    times = pd.date_range("2020-07-30", periods=14, freq="D")
    y = np.linspace(38.72, 39.42, 30)
    x = np.linspace(-122.35, -121.55, 34)
    time_signal = np.linspace(0.0, 4.0, len(times))[:, None, None]
    lat_signal = (y[None, :, None] - y.mean()) * 2.4
    lon_signal = np.cos((x[None, None, :] - x.mean()) * 12.0) * 0.8
    values = 296.0 + time_signal + lat_signal + lon_signal
    return xr.DataArray(
        values,
        coords={"time": times, "y": y, "x": x},
        dims=("time", "y", "x"),
        name="tmmx",
        attrs={"epsg": 4326, "source": "synthetic docs example"},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the docs prescribed-burn VASE panel sample.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/assets/figures/fire_vase_panel_sample.html"),
        help="HTML path for the interactive panel.",
    )
    args = parser.parse_args()

    fired_daily, fired_events = _synthetic_fired()
    climate_cube = _synthetic_climate_cube()
    panel = (
        pipe(climate_cube)
        | v.fire_vase_panel(
            fired_daily=fired_daily,
            fired_events=fired_events,
            prescribed_column="fire_type",
            prescribed_values=("prescribed burn",),
            climate_variable="tmmx",
            max_events=4,
            columns=2,
            n_ring_samples=32,
            n_theta=32,
            title="Synthetic prescribed-burn VASE panel",
        )
    ).unwrap()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    panel["fig_panel"].write_html(args.output, include_plotlyjs="cdn", full_html=True)
    print(args.output)


if __name__ == "__main__":
    main()
