from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
import zipfile
import warnings

import numpy as np
import pandas as pd
import geopandas as gpd
import requests

from cubedynamics import verbs as v


# ---------------------------------------------------------------------
# 1. Robust FIRED loader: landing page + ZIP download + local cache
# ---------------------------------------------------------------------
def load_fired_conus_ak(
    dataset_page: str = "https://scholar.colorado.edu/concern/datasets/d504rm74m",
    download_id: str = "h702q749s",
    which: str = "daily",
    prefer: str = "gpkg",
    cache_dir: str | Path | None = None,
) -> gpd.GeoDataFrame:
    """
    Load FIRED CONUS+AK daily polygons (Nov 2001–Mar 2021).

    Logic:
      • Touch dataset landing page (CU Scholar requires this)
      • Download ZIP containing FIRED
      • Extract gpkg/shp layer
      • Cache locally at ~/.fired_cache
    """
    assert which in ("events", "daily")
    assert prefer in ("gpkg", "shp")

    cache_dir = Path(cache_dir or (Path.home() / ".fired_cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)

    file_map = {
        ("events", "gpkg"): "fired_conus-ak_events_nov2001-march2021.gpkg",
        ("events", "shp"):  "fired_conus-ak_events_nov2001-march2021.shp",
        ("daily", "gpkg"):  "fired_conus-ak_daily_nov2001-march2021.gpkg",
        ("daily", "shp"):   "fired_conus-ak_daily_nov2001-march2021.shp",
    }
    primary_name = file_map[(which, prefer)]
    cached_path = cache_dir / primary_name

    # If already cached → immediate load
    if cached_path.exists():
        gdf = gpd.read_file(cached_path)
        if gdf.crs:
            gdf = gdf.to_crs("EPSG:4326")
        else:
            gdf = gdf.set_crs("EPSG:4326")
        return gdf

    # --- Robust HTTP path ---
    sess = requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Referer": dataset_page,
        "Connection": "keep-alive",
    }

    # Touch landing page
    r0 = sess.get(dataset_page, headers=headers, timeout=120)
    r0.raise_for_status()

    # Download ZIP
    zip_url = f"https://scholar.colorado.edu/downloads/{download_id}"
    resp = sess.get(zip_url, headers=headers, stream=True, timeout=300, allow_redirects=True)
    resp.raise_for_status()

    ct = resp.headers.get("Content-Type", "")
    cd_hdr = resp.headers.get("Content-Disposition", "")
    if ("zip" not in ct.lower()) and (".zip" not in cd_hdr.lower()):
        warnings.warn("Response does not clearly indicate a ZIP; continuing anyway.")

    # Extract the chosen layer
    with tempfile.TemporaryDirectory() as td:
        zpath = Path(td) / "fired.zip"
        with open(zpath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)

        with zipfile.ZipFile(zpath, "r") as z:
            names = z.namelist()
            alt_ext = "shp" if prefer == "gpkg" else "gpkg"
            alt_name = file_map[(which, alt_ext)]
            candidates = [primary_name, alt_name]

            chosen = None
            for cand in candidates:
                if cand in names:
                    chosen = cand
                    break

            if chosen is None:
                for n in names:
                    if which in n and (n.endswith(".gpkg") or n.endswith(".shp")):
                        chosen = n
                        break

            if chosen is None:
                raise RuntimeError(
                    f"Could not find FIRED file inside ZIP for {which} "
                    f"(tried {primary_name!r} and {alt_name!r})."
                )

            z.extract(chosen, path=cache_dir)
            gpath = cache_dir / chosen

    gdf = gpd.read_file(gpath)
    if gdf.crs:
        gdf = gdf.to_crs("EPSG:4326")
    else:
        gdf = gdf.set_crs("EPSG:4326")

    # Rename to primary_name if needed
    if gpath != cached_path:
        gpath.replace(cached_path)

    return gdf


# ---------------------------------------------------------------------
# 2. GRIDMET temporal support + event picker
# ---------------------------------------------------------------------
@dataclass
class TemporalSupport:
    start: pd.Timestamp
    end: pd.Timestamp | None = None


GRIDMET_SUPPORT = TemporalSupport(start=pd.Timestamp("1980-01-01"), end=None)


def pick_event_with_joint_support(
    fired_daily: gpd.GeoDataFrame,
    *,
    climate_support: TemporalSupport,
    time_buffer_days: int = 14,
    min_days: int = 3,
    id_col: str = "id",
    date_col: str = "date",
):
    """
    Select a FIRED event whose *buffered* time window is fully inside
    the climate dataset’s support window.
    """
    df = fired_daily[[id_col, date_col]].copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()

    grp = df.groupby(id_col)[date_col].agg(["min", "max"])
    grp["duration_days"] = (grp["max"] - grp["min"]).dt.days + 1

    buffer = pd.Timedelta(days=time_buffer_days)
    early_ok = grp["min"] >= (climate_support.start + buffer)

    if climate_support.end is not None:
        late_ok = grp["max"] <= (climate_support.end - buffer)
    else:
        late_ok = True

    long_enough = grp["duration_days"] >= min_days
    mask = early_ok & late_ok & long_enough

    cand = grp[mask].sort_values("min")
    if cand.empty:
        raise ValueError("No FIRED events lie within the climate support range.")

    chosen_id = cand.index[0]
    t0 = cand.loc[chosen_id, "min"]
    t1 = cand.loc[chosen_id, "max"]
    print(f"[Event Picker] id={chosen_id}, {t0.date()} → {t1.date()}, "
          f"duration={int((t1-t0).days)+1} days")
    return chosen_id


# ---------------------------------------------------------------------
# 3. Main demo: load FIRED → pick event → call v.fire_plot
# ---------------------------------------------------------------------
if __name__ == "__main__":
    print("[Demo] Loading FIRED daily...")
    fired_daily = load_fired_conus_ak(which="daily", prefer="gpkg")

    example_event_id = pick_event_with_joint_support(
        fired_daily,
        climate_support=GRIDMET_SUPPORT,
        time_buffer_days=1,
        min_days=44,
    )

    print(f"[Demo] Running fire_plot on event {example_event_id}")
    results = v.fire_plot(
        fired_daily=fired_daily,
        event_id=example_event_id,
        climate_variable="tmmx",  # or "vpd"
        time_buffer_days=1,
        n_ring_samples=200,
        n_theta=296,
        show_hist=True,
        save_prefix=None,
    )

    print("[Demo] Keys available in results:", results.keys())
