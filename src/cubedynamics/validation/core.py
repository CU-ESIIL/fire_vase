"""Shared result and path contracts for Fire VASE validation modules."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any


@dataclass
class QAResult:
    """One independently runnable validation result."""

    module: str
    status: str
    summary: str
    metrics: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.as_dict(), indent=2, default=str), encoding="utf-8")
        return output


@dataclass(frozen=True)
class ValidationPaths:
    """Resolved repository, source-cache, table, and output locations."""

    repo_root: Path
    data_root: Path
    fired_daily: Path
    fired_events: Path
    gridmet_cache: Path
    table_root: Path
    output_root: Path

    @classmethod
    def discover(
        cls,
        *,
        repo_root: str | Path | None = None,
        data_root: str | Path | None = None,
        output_root: str | Path | None = None,
    ) -> "ValidationPaths":
        root = Path(repo_root or Path(__file__).resolve().parents[3]).resolve()
        requested_data = Path(data_root).resolve() if data_root else None
        candidates = [
            requested_data,
            root / "data_lake" / "fire-vase-data-lake-v0.1" / "files",
            root,
        ]
        required = Path("artifacts/fire-vase-gridmet-real/fired-cache/fired_conus-ak_daily_nov2001-march2021.gpkg")
        resolved_data = next((candidate for candidate in candidates if candidate and (candidate / required).exists()), None)
        if resolved_data is None:
            searched = ", ".join(str(path) for path in candidates if path)
            raise FileNotFoundError(
                "Could not locate the materialized Fire VASE data lake. "
                f"Searched: {searched}. Restore data_lake/.../files or pass --data-root."
            )

        artifact_root = resolved_data / "artifacts" / "fire-vase-gridmet-real"
        tables = resolved_data / "scratch" / "fire_vase_run_full" / "tables"
        return cls(
            repo_root=root,
            data_root=resolved_data,
            fired_daily=artifact_root / "fired-cache" / "fired_conus-ak_daily_nov2001-march2021.gpkg",
            fired_events=artifact_root / "fired-cache" / "fired_conus-ak_events_nov2001-march2021.gpkg",
            gridmet_cache=artifact_root / "gridmet-cache",
            table_root=tables,
            output_root=Path(output_root or root / "output" / "validation").resolve(),
        )


def json_ready(value: Any) -> Any:
    """Convert common NumPy/Pandas scalars into JSON-friendly values."""

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, Path):
        return value.as_posix()
    return value


def write_metrics_csv(records: list[dict[str, Any]], path: str | Path) -> Path:
    """Write a small QA metrics table without adding a pandas dependency here."""

    import pandas as pd

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(output, index=False)
    return output
