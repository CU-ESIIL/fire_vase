"""Partition helpers for fire VASE lakehouse tables."""

from __future__ import annotations

from pathlib import Path


def region_from_lonlat(lon: float, lat: float) -> str:
    """Return a coarse deterministic region label from fire centroid coordinates."""

    if lat >= 50 and -170 <= lon <= -130:
        return "alaska"
    if 18 <= lat <= 23 and -161 <= lon <= -154:
        return "hawaii"
    if not (-125 <= lon <= -66 and 24 <= lat <= 50):
        return "outside_conus"
    if lon < -112:
        return "west"
    if lon < -96:
        return "intermountain"
    if lon < -84:
        return "central"
    return "east"


def spatial_bucket(lon: float, lat: float, *, size_degrees: float = 1.0) -> str:
    """Bucket centroids into stable degree tiles without using fire_id partitions."""

    if size_degrees <= 0:
        raise ValueError("size_degrees must be positive")
    lat_floor = int(lat // size_degrees)
    lon_floor = int(lon // size_degrees)
    lat_prefix = "n" if lat_floor >= 0 else "s"
    lon_prefix = "e" if lon_floor >= 0 else "w"
    return f"{lat_prefix}{abs(lat_floor):03d}_{lon_prefix}{abs(lon_floor):04d}"


def partition_path(
    table: str,
    *,
    year: int,
    lon: float,
    lat: float,
    processing_version: str,
    base: str | Path | None = None,
    region: str | None = None,
    bucket_size_degrees: float = 1.0,
) -> Path:
    """Build a lakehouse partition path.

    Partitions are intentionally cohort-friendly: table/year/region/spatial
    bucket/processing version. Fire IDs belong in records, not path names.
    """

    if "fire_id" in table.lower():
        raise ValueError("table names must not encode fire_id partitions")
    clean_version = processing_version.replace("/", "_")
    root = Path(base) if base is not None else Path()
    return root.joinpath(
        table,
        f"year={int(year)}",
        f"region={region or region_from_lonlat(lon, lat)}",
        f"spatial_bucket={spatial_bucket(lon, lat, size_degrees=bucket_size_degrees)}",
        f"processing_version={clean_version}",
    )
