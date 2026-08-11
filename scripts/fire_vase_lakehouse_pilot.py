#!/usr/bin/env python3
"""Create a small real-data fire VASE lakehouse pilot manifest.

This script never fabricates rows. If the configured source catalog has fewer
fires than the requested sample size, it writes all available fires and records
that limitation in the pilot report.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from cubedynamics.fire_vase_lakehouse import (
    ProcessingRecord,
    geometry_key,
    invalidated_components,
    medoid_by_traits,
    region_from_lonlat,
    select_cohort,
    transition,
)
from cubedynamics.fire_vase_lakehouse.cache import climate_key, event_key, vase_key


def _slug(value: Any) -> str:
    text = str(value or "unknown").strip().lower()
    return "".join(char if char.isalnum() else "_" for char in text).strip("_") or "unknown"


def _read_config(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _read_source_catalog(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".gpkg", ".geojson", ".shp"}:
        import geopandas as gpd

        gdf = gpd.read_file(path)
        if "id" in gdf.columns and "event_id" not in gdf.columns:
            gdf["event_id"] = gdf["id"]
        if "tot_ar_km2" in gdf.columns and "final_area_km2" not in gdf.columns:
            gdf["final_area_km2"] = gdf["tot_ar_km2"]
        if "event_dur" in gdf.columns and "duration_days" not in gdf.columns:
            gdf["duration_days"] = gdf["event_dur"]
        if "last_date" in gdf.columns and "observed_end" not in gdf.columns:
            gdf["observed_end"] = gdf["last_date"]
        if "ig_date" in gdf.columns and "observed_start" not in gdf.columns:
            gdf["observed_start"] = gdf["ig_date"]
        if "geometry" in gdf.columns:
            projected = gdf.to_crs("EPSG:5070").geometry.centroid
            centroids = projected.to_crs("EPSG:4326")
            gdf["centroid_lon"] = centroids.x
            gdf["centroid_lat"] = centroids.y
            gdf = gdf.drop(columns=["geometry"])
        return pd.DataFrame(gdf)
    return pd.read_csv(path)


def _stratified_sample(frame: pd.DataFrame, sample_size: int, seed: int) -> tuple[pd.DataFrame, str]:
    if sample_size >= len(frame):
        return frame.copy(), "source_catalog_smaller_than_requested_sample"
    if "size_bin" not in frame.columns:
        return frame.sample(n=sample_size, random_state=seed).copy(), "random_sample_no_size_bin"
    bins = sorted(frame["size_bin"].dropna().unique())
    per_bin = max(1, sample_size // max(1, len(bins)))
    parts: list[pd.DataFrame] = []
    for _, group in frame.groupby("size_bin", sort=True):
        take = min(len(group), per_bin)
        parts.append(group.sample(n=take, random_state=seed))
    sampled = pd.concat(parts).drop_duplicates()
    if len(sampled) < sample_size:
        remainder = frame.drop(index=sampled.index)
        if len(remainder):
            sampled = pd.concat(
                [sampled, remainder.sample(n=min(sample_size - len(sampled), len(remainder)), random_state=seed)]
            )
    return sampled.head(sample_size).copy(), "size_stratified_sample"


def _write_table(frame: pd.DataFrame, path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        frame.to_parquet(path.with_suffix(".parquet"), index=False)
        return path.with_suffix(".parquet").as_posix()
    except Exception:
        frame.to_csv(path.with_suffix(".csv"), index=False)
        return path.with_suffix(".csv").as_posix()


def run(config_path: Path, output_root: Path, sample_size: int | None = None) -> dict[str, Any]:
    start = time.perf_counter()
    config = _read_config(config_path)
    run_config = config.get("run", {})
    versions = config.get("versions", {})
    source_uri = Path(config["source"]["fire_catalog_uri"])
    requested = int(sample_size or run_config.get("sample_size", 1000))
    seed = int(run_config.get("random_seed", 20260721))
    output_root.mkdir(parents=True, exist_ok=True)

    source = _read_source_catalog(source_uri)
    sampled, sample_note = _stratified_sample(source, requested, seed)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    run_id = f"pilot-{now.replace(':', '').replace('+', 'z')}"

    records: list[dict[str, Any]] = []
    catalogs: list[dict[str, Any]] = []
    traits: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    for row in sampled.to_dict("records"):
        fire_id = str(row.get("event_id") or row.get("fire_id"))
        year = int(str(row.get("ig_date") or row.get("observed_start"))[:4])
        lon = float(row["centroid_lon"]) if "centroid_lon" in row and pd.notna(row["centroid_lon"]) else None
        lat = float(row["centroid_lat"]) if "centroid_lat" in row and pd.notna(row["centroid_lat"]) else None
        region = region_from_lonlat(lon, lat) if lon is not None and lat is not None else _slug(row.get("eco_name"))
        source_hash = str(row.get("payload_hash") or row.get("event_id") or fire_id)
        geom_key = geometry_key(
            fire_id,
            source_geometry_hash=source_hash,
            geometry_version=versions.get("geometry", "geometry-v0"),
        )
        clim_key = climate_key(
            fire_id,
            geometry_cache_key=geom_key,
            climate_source=config.get("climate", {}).get("source", "gridmet"),
            variables=list(config.get("climate", {}).get("variables", {}).values()),
            temporal_resolution=config.get("climate", {}).get("temporal_resolution", "hourly"),
            climate_version=versions.get("climate", "climate-v0"),
        )
        evt_key = event_key(
            fire_id,
            climate_cache_key=clim_key,
            event_version=versions.get("events", "events-v0"),
            method="pilot_manifest_only",
            parameters={"sample_note": sample_note},
        )
        vs_key = vase_key(
            fire_id,
            geometry_cache_key=geom_key,
            climate_cache_key=clim_key,
            vase_version=versions.get("vase", "vase-v0"),
            parameters={"temporal_resolution": config.get("climate", {}).get("temporal_resolution", "hourly")},
        )
        manifest = ProcessingRecord(
            fire_id=fire_id,
            run_id=run_id,
            component_versions=versions,
        )
        manifest = transition(transition(manifest, "running"), "geometry_complete")
        manifests.append(
            {
                "fire_id": manifest.fire_id,
                "run_id": manifest.run_id,
                "status": manifest.status,
                "component_versions": dict(manifest.component_versions),
                "attempts": manifest.attempts,
                "failure_reason": manifest.failure_reason,
                "updated_at": manifest.updated_at,
            }
        )
        total_area = float(row.get("final_area_km2", 0.0))
        duration_days = row.get("event_dur", row.get("duration_days", 0.0))
        duration_hours = float(duration_days or 0.0) * 24.0
        trait = {
            "fire_id": fire_id,
            "trait_version": versions.get("traits", "trait-v0"),
            "processing_version": run_config.get("processing_version", "fvase-lakehouse-v0"),
            "year": year,
            "region": region,
            "total_area_km2": total_area,
            "duration_hours": duration_hours,
            "peak_growth_km2_per_hour": total_area / duration_hours if duration_hours else 0.0,
            "geometry_cache_key": geom_key,
            "climate_cache_key": clim_key,
            "event_cache_key": evt_key,
        }
        traits.append(trait)
        catalogs.append(
            {
                "fire_id": fire_id,
                "catalog_version": "pilot",
                "year": year,
                "region": region,
                "processing_version": trait["processing_version"],
                "latest_manifest_status": manifest.status,
                "geometry_cache_key": geom_key,
                "climate_cache_key": clim_key,
                "vase_cache_key": vs_key,
            }
        )
        records.append({"fire_id": fire_id, "year": year, "region": region, "source_geometry_hash": source_hash})

    table_root = output_root / "tables"
    outputs = {
        "fire_catalog": _write_table(pd.DataFrame(catalogs), table_root / "fire_catalog"),
        "fire_traits": _write_table(pd.DataFrame(traits), table_root / "fire_traits"),
        "processing_manifest": _write_table(pd.DataFrame(manifests), table_root / "processing_manifest"),
        "sample_records": _write_table(pd.DataFrame(records), table_root / "sample_records"),
    }

    cohort = select_cohort(traits, region=traits[0]["region"]) if traits else []
    medoid_candidates = list(cohort or traits)
    if len(medoid_candidates) > 1000:
        medoid_candidates = medoid_candidates[:1000]
    medoid = medoid_by_traits(medoid_candidates, ["total_area_km2", "duration_hours"]) if medoid_candidates else {}
    report = {
        "run_id": run_id,
        "requested_sample_size": requested,
        "actual_sample_size": len(sampled),
        "sample_note": sample_note,
        "source_catalog_uri": source_uri.as_posix(),
        "source_catalog_rows": len(source),
        "outputs": outputs,
        "medoid_fire_id": medoid.get("fire_id"),
        "invalidated_by_climate_update": invalidated_components(["climate"]),
        "elapsed_seconds": round(time.perf_counter() - start, 3),
    }
    (output_root / "pilot_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/fire_vase_pipeline.yml")
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--sample-size", type=int, default=None)
    args = parser.parse_args()
    config_path = Path(args.config)
    config = _read_config(config_path)
    output_root = Path(args.output_root or config.get("run", {}).get("output_root", "./scratch/fire_vase_run"))
    report = run(config_path, output_root, args.sample_size)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
