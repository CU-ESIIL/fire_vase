#!/usr/bin/env python3
"""Prepare a full Fire VASE data-lake handoff.

This script can either inventory the complete lake or materialize it into an
ignored handoff directory. Use `--mode manifest` first; use `--mode hardlink`
for a local no-duplicate handoff on the same filesystem; use `--mode copy` when
preparing a directory for external drives or cloud upload.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError as exc:  # pragma: no cover
    raise SystemExit("Missing PyYAML. Install with `python -m pip install PyYAML`.") from exc


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def git_value(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.exists():
        return []
    return sorted(p for p in path.rglob("*") if p.is_file())


def expand_repo_patterns(patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for match in glob.glob(str(ROOT / pattern), recursive=True):
            path = Path(match)
            if not path.is_file():
                continue
            if path in seen:
                continue
            seen.add(path)
            out.append(path)
    return sorted(out)


def kind_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".gpkg", ".geojson", ".geoparquet"}:
        return "geospatial"
    if suffix in {".nc", ".nc4", ".zarr"}:
        return "climate-cache"
    if suffix == ".parquet":
        return "lakehouse-table"
    if suffix in {".csv", ".json"}:
        return "tabular-or-manifest"
    if suffix in {".png", ".svg", ".pdf", ".docx", ".html"}:
        return "publication-artifact"
    return "file"


def link_or_copy(src: Path, dest: Path, mode: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if mode == "manifest":
        return
    if dest.exists():
        dest.unlink()
    if mode == "copy":
        shutil.copy2(src, dest)
    elif mode == "hardlink":
        os.link(src, dest)
    else:  # pragma: no cover
        raise ValueError(f"Unknown mode {mode}")


def add_row(
    rows: list[dict[str, Any]],
    *,
    src: Path,
    dest_rel: Path,
    role: str,
    source_root: str,
    checksum: bool,
) -> None:
    stat = src.stat()
    rows.append(
        {
            "path": dest_rel.as_posix(),
            "source_path": src.as_posix(),
            "source_root": source_root,
            "role": role,
            "kind": kind_for(src),
            "format": src.suffix.lower().lstrip("."),
            "size_bytes": stat.st_size,
            "modified_utc": dt.datetime.fromtimestamp(
                stat.st_mtime, tz=dt.timezone.utc
            ).isoformat(),
            "sha256": sha256_file(src) if checksum else "",
        }
    )


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = [
        "path",
        "source_path",
        "source_root",
        "role",
        "kind",
        "format",
        "size_bytes",
        "modified_utc",
        "sha256",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_checksums(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            if row.get("sha256"):
                handle.write(f"{row['sha256']}  {row['path']}\n")


def write_readme(path: Path, manifest: dict[str, Any], config: dict[str, Any]) -> None:
    release = config.get("release", {})
    lines = [
        f"# {release.get('title', manifest['release_id'])}",
        "",
        str(release.get("description", "")).strip(),
        "",
        "## Handoff Modes",
        "",
        "- `manifest`: inventory only; no data files are copied.",
        "- `hardlink`: materializes files without duplicating bytes; fails if hardlinks are unavailable.",
        "- `copy`: creates an independent data-lake directory for sharing.",
        "",
        "## Contents",
        "",
        "- `manifest.json`: machine-readable package metadata.",
        "- `file_manifest.csv`: complete file inventory and original source paths.",
        "- `checksums.sha256`: SHA-256 checksums when generated with `--checksum`.",
        "- `files/`: present only for `hardlink` or `copy` modes.",
        "",
        "## Restore",
        "",
        "Copy or sync the contents of `files/` into the repository root so paths such as",
        "`artifacts/fire-vase-gridmet-real/` and `scratch/fire_vase_run_full/` exist.",
        "",
        "## Reproduction Commands",
        "",
    ]
    for command in config.get("reproduction", {}).get("main_workflow", []):
        lines.append(f"- `{command}`")
    lines.extend(["", "## Upstream Terms", "", str(release.get("license_note", "")).strip(), ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def build_package(
    *,
    config_path: Path,
    output_root: Path,
    mode: str,
    checksum: bool,
    include_repo_products: bool,
) -> Path:
    config = load_yaml(config_path)
    release_id = config.get("release", {}).get("id", "fire-vase-data-lake")
    package_root = output_root / release_id
    files_root = package_root / "files"
    if package_root.exists() and mode != "manifest":
        shutil.rmtree(package_root)
    package_root.mkdir(parents=True, exist_ok=True)
    if mode != "manifest":
        files_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    missing_roots: list[dict[str, str]] = []

    for root_def in config.get("local_source_roots", []):
        source = Path(root_def["source"]).expanduser()
        destination = Path(root_def["destination"])
        role = root_def.get("role", "data")
        files = iter_files(source)
        if not files:
            missing_roots.append(
                {
                    "source": source.as_posix(),
                    "destination": destination.as_posix(),
                    "role": role,
                }
            )
            continue
        for src in files:
            rel_under_source = src.relative_to(source)
            dest_rel = destination / rel_under_source
            link_or_copy(src, files_root / dest_rel, mode)
            add_row(
                rows,
                src=src,
                dest_rel=Path("files") / dest_rel,
                role=role,
                source_root=source.as_posix(),
                checksum=checksum,
            )

    if include_repo_products:
        repo_collection = config.get("collections", {}).get("repository_products", {})
        patterns = repo_collection.get("include", [])
        for src in expand_repo_patterns(patterns):
            rel = src.relative_to(ROOT)
            dest_rel = Path("repository") / rel
            link_or_copy(src, files_root / dest_rel, mode)
            add_row(
                rows,
                src=src,
                dest_rel=Path("files") / dest_rel,
                role=repo_collection.get("role", "repository-product"),
                source_root=ROOT.as_posix(),
                checksum=checksum,
            )

    rows.sort(key=lambda row: row["path"])
    total_size = sum(int(row["size_bytes"]) for row in rows)
    manifest = {
        "release_id": release_id,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": mode,
        "checksum": checksum,
        "repository": config.get("release", {}).get("source_snapshot", {}).get("repository"),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_dirty": bool(git_value("status", "--short")),
        "file_count": len(rows),
        "total_size_bytes": total_size,
        "total_size_gb": round(total_size / 1024**3, 3),
        "missing_roots": missing_roots,
        "source_roots": config.get("local_source_roots", []),
        "external_inputs": config.get("external_inputs", []),
        "reproduction": config.get("reproduction", {}),
    }

    write_csv(rows, package_root / "file_manifest.csv")
    write_checksums(rows, package_root / "checksums.sha256")
    (package_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    write_readme(package_root / "README.md", manifest, config)
    return package_root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config/data_release.yml")
    parser.add_argument("--output-root", type=Path, default=ROOT / "data_lake")
    parser.add_argument(
        "--mode",
        choices=("manifest", "hardlink", "copy"),
        default="manifest",
        help="manifest inventories only; hardlink/copy materialize files under files/.",
    )
    parser.add_argument("--checksum", action="store_true", help="Compute SHA-256 checksums.")
    parser.add_argument(
        "--skip-repo-products",
        action="store_true",
        help="Only include external lake roots, not repo-side figures/outputs/docs.",
    )
    args = parser.parse_args()
    package_root = build_package(
        config_path=args.config,
        output_root=args.output_root,
        mode=args.mode,
        checksum=args.checksum,
        include_repo_products=not args.skip_repo_products,
    )
    print(f"Wrote data lake package metadata: {package_root}")


if __name__ == "__main__":
    main()
