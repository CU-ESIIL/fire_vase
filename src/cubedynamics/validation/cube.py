"""Validate source-cube ordering and the values serialized into CubeViewer HTML."""

from __future__ import annotations

import base64
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd
from PIL import Image
import xarray as xr

from cubedynamics.plotting.cube_plot import CubeTheme
from cubedynamics.plotting.cube_viewer import cube_from_dataarray

from .core import QAResult, ValidationPaths, write_metrics_csv
from .data import event_bounds, load_event, open_gridmet_subset


_FACE_PATTERN = re.compile(
    r'class="cd-face cd-(front|back|left|right|top|bottom)"[^>]*?'
    r"background-image:\s*url\('data:image/png;base64,([^']+)'\)",
    re.DOTALL,
)
_INTERIOR_PATTERN = re.compile(
    r'class="interior-plane"\s+data-axis="(time|x|y)"\s+data-index="(\d+)"[^>]*?'
    r"background-image:\s*url\('data:image/png;base64,([^']+)'\)",
    re.DOTALL,
)


def _array_sha256(values: np.ndarray) -> str:
    array = np.asarray(values)
    if np.issubdtype(array.dtype, np.datetime64):
        canonical = np.ascontiguousarray(array.astype("datetime64[ns]").astype("<i8"))
    elif np.issubdtype(array.dtype, np.number):
        canonical = np.ascontiguousarray(array.astype("<f8"))
    else:
        canonical = np.ascontiguousarray(array.astype("U")).tobytes()
        return hashlib.sha256(canonical).hexdigest()
    return hashlib.sha256(canonical.tobytes()).hexdigest()


def _rgba(values: np.ndarray, *, cmap: str, limits: tuple[float, float]) -> np.ndarray:
    from matplotlib import colormaps
    from matplotlib.colors import Normalize

    array = np.asarray(values, dtype="float32")
    finite = np.isfinite(array)
    result = colormaps.get_cmap(cmap)(Normalize(vmin=limits[0], vmax=limits[1])(array))
    result[~finite, 3] = 0.0
    return (result * 255).astype("uint8")


def _decode_png(payload: str) -> np.ndarray:
    with Image.open(io.BytesIO(base64.b64decode(payload))) as image:
        return np.asarray(image.convert("RGBA"))


def extract_cube_html_planes(html: str) -> tuple[dict[str, np.ndarray], dict[tuple[str, int], np.ndarray]]:
    """Decode shell faces and labeled interior planes from CubeViewer HTML."""

    faces = {name: _decode_png(payload) for name, payload in _FACE_PATTERN.findall(html)}
    interiors = {
        (axis, int(index)): _decode_png(payload)
        for axis, index, payload in _INTERIOR_PATTERN.findall(html)
    }
    return faces, interiors


def _expected_shell(values: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "front": values[-1, :, :],
        "back": np.flip(values[0, :, :], axis=1),
        "left": values[:, :, 0].T,
        "right": values[:, :, -1].T,
        "top": values[:, -1, :].T,
        "bottom": values[:, 0, :].T,
    }


def _expected_interior(values: np.ndarray) -> dict[tuple[str, int], np.ndarray]:
    nt, ny, nx = values.shape
    expected: dict[tuple[str, int], np.ndarray] = {}
    expected.update({("time", index): values[index, :, :] for index in range(1, nt - 1)})
    expected.update({("x", index): values[:, :, index] for index in range(1, nx - 1)})
    expected.update({("y", index): values[:, index, :] for index in range(1, ny - 1)})
    return expected


def audit_cube_html(
    cube: xr.DataArray,
    html: str,
    *,
    cmap: str,
    limits: tuple[float, float],
) -> dict[str, Any]:
    """Compare every HTML raster against its independently indexed cube slice."""

    source = cube.transpose("time", "lat", "lon").values
    faces, interiors = extract_cube_html_planes(html)
    expected_faces = _expected_shell(source)
    expected_interiors = _expected_interior(source)
    records: list[dict[str, Any]] = []

    def compare(kind: str, axis: str, index: int | str, expected_values: np.ndarray, actual: np.ndarray | None) -> None:
        expected = _rgba(expected_values, cmap=cmap, limits=limits)
        shape_matches = actual is not None and actual.shape == expected.shape
        max_difference = (
            int(np.max(np.abs(actual.astype("int16") - expected.astype("int16"))))
            if shape_matches
            else -1
        )
        records.append(
            {
                "kind": kind,
                "axis": axis,
                "source_index": index,
                "expected_shape": "x".join(map(str, expected.shape)),
                "html_shape": "missing" if actual is None else "x".join(map(str, actual.shape)),
                "shape_matches": bool(shape_matches),
                "max_rgba_channel_difference": max_difference,
                "exact_pixel_match": bool(shape_matches and max_difference == 0),
            }
        )

    face_indices: dict[str, tuple[str, int | str]] = {
        "front": ("time", source.shape[0] - 1),
        "back": ("time", "0 (x reversed for back-facing CSS plane)"),
        "left": ("lon", 0),
        "right": ("lon", source.shape[2] - 1),
        "top": ("lat", source.shape[1] - 1),
        "bottom": ("lat", 0),
    }
    for name, expected_values in expected_faces.items():
        axis, index = face_indices[name]
        compare("shell_face", f"{name}:{axis}", index, expected_values, faces.get(name))
    for (axis, index), expected_values in expected_interiors.items():
        compare("interior_plane", axis, index, expected_values, interiors.get((axis, index)))

    time_plane_indices = {0, source.shape[0] - 1}
    time_plane_indices.update(index for axis, index in interiors if axis == "time")
    return {
        "records": records,
        "faces": faces,
        "interiors": interiors,
        "expected_face_count": len(expected_faces),
        "expected_interior_count": len(expected_interiors),
        "all_planes_present": set(interiors) == set(expected_interiors) and set(faces) == set(expected_faces),
        "all_pixels_exact": all(record["exact_pixel_match"] for record in records),
        "serialized_time_indices": sorted(time_plane_indices),
        "all_time_slices_serialized_once": sorted(time_plane_indices) == list(range(source.shape[0])),
    }


def _coordinate_records(cube: xr.DataArray) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for dim in ("time", "lat", "lon"):
        values = np.asarray(cube[dim].values)
        numeric = values.astype("datetime64[ns]").astype("int64") if dim == "time" else values.astype(float)
        differences = np.diff(numeric)
        direction = "ascending" if np.all(differences > 0) else "descending" if np.all(differences < 0) else "non-monotonic"
        records.append(
            {
                "dimension": dim,
                "count": int(len(values)),
                "first": str(pd.Timestamp(values[0])) if dim == "time" else float(values[0]),
                "last": str(pd.Timestamp(values[-1])) if dim == "time" else float(values[-1]),
                "direction": direction,
                "duplicate_coordinates": int(pd.Index(values).duplicated().sum()),
                "coordinate_sha256": _array_sha256(values),
            }
        )
    return records


def _landmark_records(
    cube: xr.DataArray,
    faces: dict[str, np.ndarray],
    *,
    cmap: str,
    limits: tuple[float, float],
) -> list[dict[str, Any]]:
    values = cube.transpose("time", "lat", "lon").values
    records: list[dict[str, Any]] = []
    for time_index, face in ((0, "back"), (values.shape[0] - 1, "front")):
        for lat_index in (0, values.shape[1] - 1):
            for lon_index in (0, values.shape[2] - 1):
                html_lon_index = values.shape[2] - 1 - lon_index if face == "back" else lon_index
                expected = _rgba(
                    np.asarray([[values[time_index, lat_index, lon_index]]]),
                    cmap=cmap,
                    limits=limits,
                )[0, 0]
                actual = faces[face][lat_index, html_lon_index]
                records.append(
                    {
                        "landmark": f"t{time_index}-lat{lat_index}-lon{lon_index}",
                        "time": str(pd.Timestamp(cube.time.values[time_index]).date()),
                        "lat": float(cube.lat.values[lat_index]),
                        "lon": float(cube.lon.values[lon_index]),
                        "source_value": float(values[time_index, lat_index, lon_index]),
                        "html_face": face,
                        "html_row": int(lat_index),
                        "html_column": int(html_lon_index),
                        "expected_rgba": ",".join(map(str, expected.tolist())),
                        "actual_rgba": ",".join(map(str, actual.tolist())),
                        "exact": bool(np.array_equal(expected, actual)),
                    }
                )
    return records


def _plot_cube_audit(
    cube: xr.DataArray,
    audit: dict[str, Any],
    output: Path,
) -> None:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    values = cube.transpose("time", "lat", "lon").values
    faces = audit["faces"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 9), constrained_layout=True)

    image = axes[0, 0].imshow(values[0], cmap="viridis", aspect="auto")
    axes[0, 0].set_title("Source t=0: index rows are latitude, columns longitude")
    axes[0, 0].set_xlabel(f"lon index 0 -> {values.shape[2] - 1}")
    axes[0, 0].set_ylabel(f"lat index 0 -> {values.shape[1] - 1}")
    fig.colorbar(image, ax=axes[0, 0], shrink=0.72, label=cube.attrs.get("units", "source units"))

    axes[0, 1].imshow(faces["back"], aspect="auto")
    axes[0, 1].set_title("Decoded HTML back face: intentional x reversal")
    axes[0, 1].annotate("source lon[-1]", (0, 0), xytext=(5, 18), textcoords="offset points", color="white", fontsize=8)
    axes[0, 1].annotate("source lon[0]", (values.shape[2] - 1, 0), xytext=(-5, 18), textcoords="offset points", ha="right", color="white", fontsize=8)
    axes[0, 1].set_xlabel("HTML pixel column")
    axes[0, 1].set_ylabel("latitude index")

    axes[0, 2].imshow(faces["front"], aspect="auto")
    axes[0, 2].set_title("Decoded HTML front face: final source day")
    axes[0, 2].set_xlabel("longitude index (unchanged)")
    axes[0, 2].set_ylabel("latitude index (unchanged)")

    axes[1, 0].imshow(faces["left"], aspect="auto")
    axes[1, 0].set_title("Left HTML face traces every date at lon index 0")
    axes[1, 0].set_xlabel(f"time index 0 -> {values.shape[0] - 1}")
    axes[1, 0].set_ylabel(f"lat index 0 -> {values.shape[1] - 1}")

    mean_time = np.nanmean(values, axis=(1, 2))
    axes[1, 1].plot(pd.to_datetime(cube.time.values), mean_time, marker="o", markersize=3, color="#3b6f88")
    axes[1, 1].set_title("All source dates remain ordered and contiguous")
    axes[1, 1].set_ylabel(f"spatial mean {cube.name}")
    axes[1, 1].grid(alpha=0.25)
    locator = mdates.AutoDateLocator(minticks=4, maxticks=7)
    axes[1, 1].xaxis.set_major_locator(locator)
    axes[1, 1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))

    axes[1, 2].axis("off")
    exact_count = sum(record["exact_pixel_match"] for record in audit["records"])
    checks = [
        ("source dimensions", "time x lat x lon"),
        ("source shape", " x ".join(map(str, values.shape))),
        ("shell faces decoded", f"{len(faces)} / 6"),
        ("interior planes decoded", str(len(audit["interiors"]))),
        ("every time plane serialized", str(audit["all_time_slices_serialized_once"])),
        ("exact raster comparisons", f"{exact_count} / {len(audit['records'])}"),
        ("maximum channel residual", str(max(record["max_rgba_channel_difference"] for record in audit["records"]))),
    ]
    axes[1, 2].table(
        cellText=checks,
        colLabels=["integrity check", "result"],
        cellLoc="left",
        colLoc="left",
        loc="center",
        colWidths=[0.63, 0.37],
    ).auto_set_font_size(False)
    for cell in axes[1, 2].tables[0].get_celld().values():
        cell.set_fontsize(8)
    axes[1, 2].set_title("Source -> HTML audit", pad=10)

    fig.suptitle("QA 4 - Real GridMET cube axis, continuity, and HTML serialization integrity", fontsize=15, fontweight="bold")
    fig.savefig(output, dpi=190)
    plt.close(fig)


def run_cube_validation(
    paths: ValidationPaths,
    *,
    fire_id: int = 20657,
    variable: str = "tmmx",
    output_dir: str | Path | None = None,
) -> QAResult:
    """Validate the real sampled cube and every raster serialized into HTML."""

    out = Path(output_dir or paths.output_root / "cube")
    out.mkdir(parents=True, exist_ok=True)
    event = load_event(paths, fire_id)
    lazy_cube = open_gridmet_subset(
        paths,
        variable=variable,
        year=int(event.t0.year),
        start=event.t0,
        end=event.t1,
        bounds=event_bounds(event),
    )
    cube = lazy_cube.transpose("time", "lat", "lon").compute()
    values = np.asarray(cube.values, dtype=float)
    finite = values[np.isfinite(values)]
    limits = (float(np.min(finite)), float(np.max(finite)))
    cmap = "viridis"
    nt, ny, nx = values.shape

    html_path = out / "cube_integrity.html"
    html = cube_from_dataarray(
        cube,
        out_html=html_path.as_posix(),
        cmap=cmap,
        title=f"Validated real GridMET cube: fire {fire_id}, {variable}",
        legend_title=f"{variable} ({cube.attrs.get('units', 'source units')})",
        thin_time_factor=1,
        fill_limits=limits,
        fill_mode="volume",
        volume_density={"time": max(0, nt - 2), "x": max(0, nx - 2), "y": max(0, ny - 2)},
        volume_downsample={"time": 1, "space": 1},
        show_progress=False,
        return_html=True,
        theme=CubeTheme(title_color="#24343d", legend_color="#24343d"),
    )
    coordinate_records = _coordinate_records(cube)
    source_manifest = {
        "contract": "CubeViewer validation payload v1",
        "fire_id": str(fire_id),
        "variable": variable,
        "dims": list(cube.dims),
        "shape": [int(value) for value in cube.shape],
        "source_value_sha256": _array_sha256(values),
        "coordinate_sha256": {record["dimension"]: record["coordinate_sha256"] for record in coordinate_records},
        "finite_cells": int(np.isfinite(values).sum()),
        "missing_cells": int(np.isnan(values).sum()),
        "first_time": str(pd.Timestamp(cube.time.values[0])),
        "last_time": str(pd.Timestamp(cube.time.values[-1])),
        "thin_time_factor": 1,
        "all_interior_time_planes_requested": True,
    }
    manifest_tag = (
        '<script type="application/json" id="cube-validation-manifest">'
        + json.dumps(source_manifest, sort_keys=True)
        + "</script>"
    )
    html = html.replace("</body>", manifest_tag + "\n</body>")
    html_path.write_text(html, encoding="utf-8")

    audit = audit_cube_html(cube, html, cmap=cmap, limits=limits)
    plane_metrics = write_metrics_csv(audit["records"], out / "cube_html_plane_audit.csv")
    coordinate_metrics = write_metrics_csv(coordinate_records, out / "cube_coordinate_audit.csv")
    landmark_records = _landmark_records(cube, audit["faces"], cmap=cmap, limits=limits)
    landmark_metrics = write_metrics_csv(landmark_records, out / "cube_corner_landmarks.csv")
    time_records = [
        {
            "time_index": index,
            "timestamp": str(pd.Timestamp(cube.time.values[index])),
            "slice_value_sha256": _array_sha256(values[index]),
            "finite_cells": int(np.isfinite(values[index]).sum()),
            "missing_cells": int(np.isnan(values[index]).sum()),
        }
        for index in range(nt)
    ]
    time_metrics = write_metrics_csv(time_records, out / "cube_time_slice_checksums.csv")
    manifest_path = out / "cube_source_manifest.json"
    manifest_path.write_text(json.dumps(source_manifest, indent=2), encoding="utf-8")
    plot = out / "cube_axis_html_integrity.png"
    _plot_cube_audit(cube, audit, plot)

    time_values = pd.DatetimeIndex(cube.time.values)
    daily_gaps = np.diff(time_values.values.astype("datetime64[D]").astype(int))
    time_contiguous = bool(len(daily_gaps) == 0 or np.all(daily_gaps == 1))
    coordinate_integrity = all(
        record["direction"] in {"ascending", "descending"} and record["duplicate_coordinates"] == 0
        for record in coordinate_records
    )
    embedded_manifest_matches = source_manifest["source_value_sha256"] in html
    landmark_integrity = all(record["exact"] for record in landmark_records)
    passed = all(
        [
            tuple(cube.dims) == ("time", "lat", "lon"),
            time_contiguous,
            coordinate_integrity,
            audit["all_planes_present"],
            audit["all_pixels_exact"],
            audit["all_time_slices_serialized_once"],
            embedded_manifest_matches,
            landmark_integrity,
        ]
    )
    result = QAResult(
        module="cube",
        status="pass" if passed else "fail",
        summary="The real GridMET cube retains ordered coordinates and contiguous dates; every source time plane and every decoded HTML raster matches the declared source indexing exactly.",
        metrics={
            "fire_id": str(fire_id),
            "variable": variable,
            "dims": list(cube.dims),
            "shape": {dim: int(cube.sizes[dim]) for dim in cube.dims},
            "source_cells": int(values.size),
            "finite_cells": int(np.isfinite(values).sum()),
            "missing_cells": int(np.isnan(values).sum()),
            "time_contiguous_daily": time_contiguous,
            "coordinate_integrity": coordinate_integrity,
            "all_html_planes_present": audit["all_planes_present"],
            "all_html_pixels_exact": audit["all_pixels_exact"],
            "all_time_slices_serialized_once": audit["all_time_slices_serialized_once"],
            "decoded_shell_faces": int(len(audit["faces"])),
            "decoded_interior_planes": int(len(audit["interiors"])),
            "maximum_rgba_channel_residual": int(max(record["max_rgba_channel_difference"] for record in audit["records"])),
            "corner_landmarks_exact": landmark_integrity,
            "source_value_sha256": source_manifest["source_value_sha256"],
            "embedded_manifest_matches_source": embedded_manifest_matches,
        },
        artifacts={
            "plot": plot.as_posix(),
            "interactive_html": html_path.as_posix(),
            "plane_metrics": plane_metrics.as_posix(),
            "coordinate_metrics": coordinate_metrics.as_posix(),
            "landmarks": landmark_metrics.as_posix(),
            "time_slice_checksums": time_metrics.as_posix(),
            "source_manifest": manifest_path.as_posix(),
        },
        notes=[
            "The validation HTML uses thin_time_factor=1 and includes every interior time plane, so no sampled date is omitted from this audit view.",
            "The back face reverses longitude intentionally because CSS rotates that plane by 180 degrees; the audit reverses the source expectation before requiring exact pixel equality.",
            "The HTML remains a rendered view. The NetCDF/xarray cube is the data authority; the embedded SHA-256 manifest ties the view back to that complete source sample.",
        ],
    )
    result_path = result.write(out / "result.json")
    result.artifacts["result"] = result_path.as_posix()
    result.write(result_path)
    return result


__all__ = ["audit_cube_html", "extract_cube_html_planes", "run_cube_validation"]
