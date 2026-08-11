#!/usr/bin/env python3
"""Cache yearly gridMET NetCDF files for fire VASE climate attribution."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


BASE_URL = "https://www.northwestknowledge.net/metdata/data"
STANDARD_VARIABLES = ["tmmx", "tmmn", "vpd", "vs"]
COMPREHENSIVE_VARIABLES = [
    "tmmx",
    "tmmn",
    "vpd",
    "vs",
    "pr",
    "rmax",
    "rmin",
    "sph",
    "fm100",
    "fm1000",
    "erc",
    "bi",
    "etr",
    "pet",
    "srad",
]


def _download(url: str, target: Path, *, timeout: int = 180) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        return {"path": target.as_posix(), "status": "cached", "bytes": target.stat().st_size}

    part = target.with_suffix(target.suffix + ".part")
    received = part.stat().st_size if part.exists() else 0
    headers = {"Range": f"bytes={received}-"} if received else {}
    with requests.get(url, stream=True, timeout=timeout, headers=headers) as response:
        if response.status_code == 416:
            part.replace(target)
            return {"path": target.as_posix(), "status": "cached", "bytes": target.stat().st_size}
        response.raise_for_status()
        mode = "ab" if received and response.status_code == 206 else "wb"
        with part.open(mode) as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    part.replace(target)
    return {"path": target.as_posix(), "status": "downloaded", "bytes": target.stat().st_size}


def run(args: argparse.Namespace) -> dict:
    started = time.perf_counter()
    records = []
    variables = args.variables
    if args.preset == "standard" and variables is None:
        variables = STANDARD_VARIABLES
    elif args.preset == "comprehensive" and variables is None:
        variables = COMPREHENSIVE_VARIABLES
    elif variables is None:
        raise ValueError(f"Unsupported gridMET cache preset: {args.preset!r}")
    args.cache_dir.mkdir(parents=True, exist_ok=True)
    for year in range(args.start_year, args.end_year + 1):
        for variable in variables:
            target = args.cache_dir / f"{variable}_{year}.nc"
            url = f"{BASE_URL}/{variable}_{year}.nc"
            try:
                record = _download(url, target, timeout=args.timeout)
            except Exception as exc:
                record = {
                    "path": target.as_posix(),
                    "status": "failed",
                    "error": str(exc),
                    "url": url,
                }
            record.update({"variable": variable, "year": year, "url": url})
            records.append(record)
            print(json.dumps(record), flush=True)
            if record["status"] == "failed" and not args.keep_going:
                break
        if records and records[-1]["status"] == "failed" and not args.keep_going:
            break

    summary = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "cache_dir": args.cache_dir.as_posix(),
        "start_year": args.start_year,
        "end_year": args.end_year,
        "variables": variables,
        "downloaded": sum(1 for r in records if r["status"] == "downloaded"),
        "cached": sum(1 for r in records if r["status"] == "cached"),
        "failed": sum(1 for r in records if r["status"] == "failed"),
        "total_bytes": sum(int(r.get("bytes", 0)) for r in records),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "records": records,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=Path("artifacts/fire-vase-gridmet-real/gridmet-cache"))
    parser.add_argument("--manifest", type=Path, default=Path("scratch/fire_vase_run_full/gridmet_cache_manifest.json"))
    parser.add_argument("--start-year", type=int, default=2000)
    parser.add_argument("--end-year", type=int, default=2021)
    parser.add_argument("--preset", choices=["standard", "comprehensive"], default="standard")
    parser.add_argument("--variables", nargs="+", default=None)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--keep-going", action="store_true")
    args = parser.parse_args()
    summary = run(args)
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
