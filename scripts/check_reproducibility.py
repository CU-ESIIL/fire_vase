#!/usr/bin/env python3
"""Check Fire VASE data-lake and figure reproducibility artifacts.

This script is intentionally small and explicit because it is meant to be read
by collaborators as well as run by automation. It answers three questions:

1. Does the materialized data lake match `checksums.sha256`?
2. Do regenerated derived statistics match the checked-in references?
3. Do regenerated manuscript figures look the same as the references?

Figure files are checked two ways. Byte hashes catch exact file identity, while
PNG pixel comparison catches visual identity. PDF and SVG files commonly differ
at the byte level because plotting libraries write timestamps or metadata, so
the PNG pixel result is the main "does it look the same?" test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    """Return a SHA-256 digest for `path` without loading the whole file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_data_lake(data_lake: Path) -> dict[str, Any]:
    """Verify every file named in a data-lake `checksums.sha256` file."""
    checksums = data_lake / "checksums.sha256"
    if not checksums.exists():
        return {"status": "missing", "path": checksums.as_posix(), "checked": 0, "failures": []}

    failures: list[dict[str, str]] = []
    checked = 0
    for line in checksums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        # The checksum file follows the standard `hash  relative/path` format.
        expected, rel = line.split(None, 1)
        rel = rel.strip()
        path = data_lake / rel
        checked += 1
        if not path.exists():
            failures.append({"path": rel, "reason": "missing"})
            continue
        actual = sha256_file(path)
        if actual != expected:
            failures.append({"path": rel, "reason": "sha256_mismatch", "expected": expected, "actual": actual})

    return {
        "status": "pass" if not failures else "fail",
        "path": data_lake.as_posix(),
        "checked": checked,
        "failures": failures,
    }


def compare_file_sets(generated_dir: Path, reference_dir: Path) -> dict[str, Any]:
    """Compare files with matching names in two flat directories by SHA-256."""
    failures: list[dict[str, str]] = []
    matches = 0
    checked = 0
    for ref in sorted(path for path in reference_dir.iterdir() if path.is_file()):
        gen = generated_dir / ref.name
        checked += 1
        if not gen.exists():
            failures.append({"path": ref.name, "reason": "missing_generated"})
            continue
        ref_hash = sha256_file(ref)
        gen_hash = sha256_file(gen)
        if ref_hash == gen_hash:
            matches += 1
        else:
            failures.append(
                {
                    "path": ref.name,
                    "reason": "sha256_mismatch",
                    "reference": ref_hash,
                    "generated": gen_hash,
                }
            )
    return {
        "status": "pass" if not failures else "fail",
        "checked": checked,
        "matches": matches,
        "failures": failures,
    }


def compare_png_pixels(generated: Path, reference: Path) -> dict[str, Any]:
    """Compare two PNGs by rendered pixels rather than compressed file bytes."""
    try:
        from PIL import Image, ImageChops
        import numpy as np
    except ModuleNotFoundError:
        return {"status": "skipped", "reason": "Pillow or numpy is not installed"}

    gen = Image.open(generated).convert("RGBA")
    ref = Image.open(reference).convert("RGBA")
    if gen.size != ref.size:
        return {"status": "fail", "reason": "size_mismatch", "generated_size": gen.size, "reference_size": ref.size}

    diff = ImageChops.difference(gen, ref)
    bbox = diff.getbbox()
    if bbox is None:
        return {"status": "pass", "changed_pixels": 0, "max_channel_difference": 0, "size": gen.size}

    # Count any RGB channel change as a changed pixel; alpha-only differences
    # are ignored because these exported manuscript PNGs are opaque.
    arr = np.asarray(diff)
    changed = int(np.any(arr[:, :, :3] != 0, axis=2).sum())
    return {
        "status": "fail",
        "reason": "pixel_mismatch",
        "changed_pixels": changed,
        "total_pixels": int(gen.size[0] * gen.size[1]),
        "max_channel_difference": int(arr.max()),
        "size": gen.size,
    }


def check_figures(generated_dir: Path, reference_dir: Path) -> dict[str, Any]:
    """Check manuscript Figures 1-5 by file hash and PNG pixel identity."""
    byte_results: list[dict[str, Any]] = []
    pixel_results: list[dict[str, Any]] = []
    for number in range(1, 6):
        for suffix in ("pdf", "png", "svg"):
            name = f"Figure_{number}.{suffix}"
            gen = generated_dir / name
            ref = reference_dir / name
            if not gen.exists() or not ref.exists():
                byte_results.append({"path": name, "status": "fail", "reason": "missing"})
                continue
            gen_hash = sha256_file(gen)
            ref_hash = sha256_file(ref)
            byte_results.append(
                {
                    "path": name,
                    "status": "pass" if gen_hash == ref_hash else "fail",
                    "generated": gen_hash,
                    "reference": ref_hash,
                }
            )
        name = f"Figure_{number}.png"
        gen = generated_dir / name
        ref = reference_dir / name
        if gen.exists() and ref.exists():
            result = compare_png_pixels(gen, ref)
            result["path"] = name
            pixel_results.append(result)

    return {
        "byte_status": "pass" if all(item["status"] == "pass" for item in byte_results) else "fail",
        "pixel_status": "pass" if all(item["status"] == "pass" for item in pixel_results) else "fail",
        "byte_results": byte_results,
        "pixel_results": pixel_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-lake", type=Path, default=Path("data_lake/fire-vase-data-lake-v0.1"))
    parser.add_argument("--generated-figure-dir", type=Path, default=Path("manuscript_figures"))
    parser.add_argument("--reference-figure-dir", type=Path, default=Path("figures/main"))
    parser.add_argument("--generated-stats-dir", type=Path, default=Path("manuscript_figures/derived_stats"))
    parser.add_argument("--reference-stats-dir", type=Path, default=Path("figures/main/derived_stats"))
    parser.add_argument("--skip-data-lake", action="store_true", help="Skip the full data-lake checksum pass.")
    parser.add_argument("--json-output", type=Path, default=None, help="Optional path for a JSON report.")
    args = parser.parse_args()

    report: dict[str, Any] = {}
    if not args.skip_data_lake:
        report["data_lake"] = check_data_lake(args.data_lake)
    report["derived_stats"] = compare_file_sets(args.generated_stats_dir, args.reference_stats_dir)
    report["figures"] = check_figures(args.generated_figure_dir, args.reference_figure_dir)

    text = json.dumps(report, indent=2)
    print(text)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(text + "\n", encoding="utf-8")

    failed = False
    if report.get("data_lake", {}).get("status") == "fail":
        failed = True
    if report["derived_stats"]["status"] == "fail":
        failed = True
    if report["figures"]["pixel_status"] == "fail":
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
