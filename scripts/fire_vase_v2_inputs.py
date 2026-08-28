"""Read-only source audit and day-specific spatial meteorological attribution."""
from pathlib import Path
import hashlib
import json
import sqlite3
import numpy as np
import pandas as pd
from cubedynamics.analysis_v2 import CORE, exact_transitions, validate_exposure


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4*1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_attributes(path, columns):
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        table = db.execute("select table_name from gpkg_contents").fetchone()[0]
        return pd.read_sql_query(f'SELECT {columns} FROM "{table}"',db)


def audit_inputs(data_root, output):
    table = data_root / "scratch/fire_vase_run_full/tables"
    cache = data_root / "artifacts/fire-vase-gridmet-real/fired-cache"
    daily_path = cache / "fired_conus-ak_daily_nov2001-march2021.gpkg"
    event_path = cache / "fired_conus-ak_events_nov2001-march2021.gpkg"
    required = [daily_path,event_path,table/"vase_slices.parquet",table/"fire_traits.parquet",
        data_root/"scratch/fire_vase_developmental_morphology/developmental_morphospace_features.parquet"]
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(f"Required real input unavailable: {path}")
    slices = pd.read_parquet(table/"vase_slices.parquet")
    traits = pd.read_parquet(table/"fire_traits.parquet")
    legacy = pd.read_parquet(required[-1])
    daily = read_attributes(daily_path,"id,date,event_day,event_dur,dy_ar_km2,tot_ar_km2,mx_grw_km2,lc_name,eco_name")
    events = read_attributes(event_path,"id,ig_date,last_date,event_dur,tot_ar_km2,mx_grw_km2,lc_name,eco_name")
    for d in [slices,traits,legacy]:
        d["fire_id"] = d.fire_id.astype(str)
    for d in [daily,events]:
        d["fire_id"] = d.id.astype(str)
    daily["timestamp"] = pd.to_datetime(daily.date,errors="coerce")
    slices["timestamp"] = pd.to_datetime(slices.timestamp,errors="coerce")
    merged = daily.merge(slices[["fire_id","timestamp","ring_area_km2"]],on=["fire_id","timestamp"],how="outer",indicator=True,validate="one_to_one")
    exclusions=merged.loc[merged._merge.ne("both"),["fire_id","timestamp","_merge"]].copy()
    exclusions["in_event_catalog"]=exclusions.fire_id.isin(events.fire_id)
    exclusions["reason"]=np.where(exclusions.in_event_catalog,"date_not_in_cached_slices","daily_id_absent_from_event_catalog")
    exclusions.to_csv(output/"source_row_exclusions.csv",index=False)
    both = merged._merge.eq("both")
    discrepancies = np.abs(merged.loc[both,"dy_ar_km2"]-merged.loc[both,"ring_area_km2"])
    if len(merged.loc[merged._merge.eq("right_only")]) or discrepancies.gt(1e-9).any():
        raise ValueError("Cached daily increments cannot be traced exactly to FIRED source")
    source_area = events.set_index("fire_id").tot_ar_km2.reindex(traits.fire_id).to_numpy()
    if not np.allclose(source_area,traits.total_area_km2,rtol=1e-9,atol=1e-9):
        raise ValueError("Catalog area differs from original FIRED event source")
    _, audit = exact_transitions(slices)
    audit.update(raw_daily_rows=len(daily),raw_events=len(events),cached_events=len(traits),
        source_rows_absent_from_cache=int(merged._merge.eq("left_only").sum()),
        daily_increment_max_abs_error=float(discrepancies.max()),
        source_missing_growth=int(daily.dy_ar_km2.isna().sum()),
        source_negative_growth=int(daily.dy_ar_km2.lt(0).sum()),
        mislabeled_peak_equals_catalog_mean=int(np.isclose(traits.peak_growth_km2_per_hour,
            traits.total_area_km2/traits.duration_hours).sum()),
        weather_extraction_methods=slices.climate_extraction_method.value_counts().to_dict())
    (output/"input_audit.json").write_text(json.dumps(audit,indent=2))
    hashes = {str(p.relative_to(data_root)):sha256(p) for p in required}
    (output/"input_hashes.json").write_text(json.dumps(hashes,indent=2))
    return slices,traits,legacy,events,daily


def day_t_weather(data_root, slices, output):
    """Nearest gridMET cell at the projected newly burned-area centroid on day t.

    No final-event polygon enters the computation. Geometries are daily FIRED
    growth footprints. Time lookup is exact; spatial bounds are checked before
    nearest-cell lookup (no Alaska-to-CONUS edge extrapolation).
    """
    import geopandas as gpd
    import xarray as xr
    cache = data_root/"artifacts/fire-vase-gridmet-real"
    gpkg = cache/"fired-cache/fired_conus-ak_daily_nov2001-march2021.gpkg"
    transitions,_ = exact_transitions(slices)
    out = transitions[["fire_id","timestamp"]].copy()
    expected = {"source_geometry_sha256":sha256(gpkg),
                "keys_sha256":hashlib.sha256(pd.util.hash_pandas_object(out,index=False).values.tobytes()).hexdigest(),
                "method":"day_t_newly_burned_centroid", "version":2}
    target = output/"day_t_weather.parquet"
    manifest = output/"day_t_weather_manifest.json"
    if target.exists() and manifest.exists():
        old = json.loads(manifest.read_text())
        if all(old.get(k)==v for k,v in expected.items()) and old.get("output_sha256")==sha256(target):
            # Input hashes are verified on reuse, not merely their filenames.
            if all(sha256(data_root/p)==h for p,h in old["gridmet_input_hashes"].items()):
                print("Validated day-t weather cache",flush=True)
                return pd.read_parquet(target)
    print("Reading daily geometries for prospective spatial exposure",flush=True)
    geometry = gpd.read_file(gpkg,columns=["id","date"])
    geometry["fire_id"] = geometry.id.astype(str)
    geometry["timestamp"] = pd.to_datetime(geometry.date)
    geometry = geometry.merge(out,on=["fire_id","timestamp"],validate="one_to_one")
    centers = geometry.to_crs(5070).geometry.centroid.to_crs(4326)
    geometry["exposure_lon"],geometry["exposure_lat"] = centers.x,centers.y
    out = out.merge(geometry[["fire_id","timestamp","exposure_lon","exposure_lat"]],
                    on=["fire_id","timestamp"],validate="one_to_one")
    del geometry, centers
    hashes = {}
    variables = dict(zip(["tmmx","tmmn","vpd","vs"],CORE))
    for col in CORE:
        out[col] = np.nan
    for year,part in out.groupby(out.timestamp.dt.year,sort=True):
        print(f"Sampling day-t weather: {year}, {len(part):,} transitions",flush=True)
        for variable,col in variables.items():
            path = cache/f"gridmet-cache/{variable}_{year}.nc"
            if not path.exists():
                raise FileNotFoundError(f"Required real weather file unavailable: {path}")
            hashes[str(path.relative_to(data_root))] = sha256(path)
            with xr.open_dataset(path) as ds:
                da = ds[next(iter(ds.data_vars))]
                time = "day" if "day" in da.dims else "time"
                inside = part.exposure_lon.between(float(ds.lon.min()),float(ds.lon.max())) & part.exposure_lat.between(float(ds.lat.min()),float(ds.lat.max()))
                good = part.loc[inside]
                if good.empty:
                    continue
                ti = ds.indexes[time].get_indexer(good.timestamp)
                if (ti < 0).any():
                    raise ValueError(f"Missing exact gridMET date in {path}")
                yi = ds.indexes["lat"].get_indexer(good.exposure_lat,method="nearest")
                xi = ds.indexes["lon"].get_indexer(good.exposure_lon,method="nearest")
                # Dask vectorized indexing avoids loading the whole annual cube.
                # Respect native compressed chunks. Splitting a 61-day source
                # chunk into daily tasks would decompress it up to 61 times.
                values = da.chunk({}).isel({time:xr.DataArray(ti,dims="points"),
                    "lat":xr.DataArray(yi,dims="points"),"lon":xr.DataArray(xi,dims="points")}).compute().values
                if variable in ["tmmx","tmmn"]:
                    values = values-273.15
                out.loc[good.index,col] = values
    out["exposure_geometry"] = "day_t_newly_burned_centroid"
    out["geometry_max_date"] = out.timestamp
    validate_exposure(out)
    out.to_parquet(target,index=False)
    expected.update(gridmet_input_hashes=hashes, output_sha256=sha256(target),rows=len(out),
                    complete_rows=int(out[CORE].notna().all(1).sum()))
    manifest.write_text(json.dumps(expected,indent=2))
    return out
