"""Utilities for scalable fire VASE lakehouse workflows.

The objects here describe identities, schemas, partitions, manifests, and
summary queries. Heavy storage engines such as Parquet, Zarr, and DuckDB are
kept at the pipeline/script boundary so importing cubedynamics stays light.
"""

from .cache import (
    COMPONENT_ORDER,
    build_cache_key,
    climate_key,
    event_key,
    geometry_key,
    invalidated_components,
    render_key,
    stable_json,
    vase_key,
)
from .manifest import ProcessingRecord, retry_failed, transition
from .partitioning import partition_path, region_from_lonlat, spatial_bucket
from .qc import climate_qc, geometry_qc, task_qc
from .query import event_aligned_quantiles, medoid_by_traits, select_cohort
from .schemas import load_schema, validate_records

__all__ = [
    "COMPONENT_ORDER",
    "ProcessingRecord",
    "build_cache_key",
    "climate_key",
    "climate_qc",
    "event_aligned_quantiles",
    "event_key",
    "geometry_key",
    "geometry_qc",
    "invalidated_components",
    "load_schema",
    "medoid_by_traits",
    "partition_path",
    "region_from_lonlat",
    "render_key",
    "retry_failed",
    "select_cohort",
    "spatial_bucket",
    "stable_json",
    "task_qc",
    "transition",
    "validate_records",
    "vase_key",
]
