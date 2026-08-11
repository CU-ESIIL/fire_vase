#!/usr/bin/env python3
"""Guard against committing lakehouse-scale outputs to the repository."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _load_policy(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised only in bare envs
        raise RuntimeError("PyYAML is required to read repository_policy.yml") from exc
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _git_files(mode: str) -> list[Path]:
    if mode == "staged":
        command = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    else:
        command = ["git", "ls-files"]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def _is_under(path: Path, prefixes: list[str]) -> bool:
    normalized = path.as_posix()
    return any(normalized == prefix.rstrip("/") or normalized.startswith(prefix.rstrip("/") + "/") for prefix in prefixes)


def _has_blocked_extension(path: Path, blocked_extensions: set[str]) -> bool:
    suffixes = {suffix.lower() for suffix in path.suffixes}
    if suffixes.intersection(blocked_extensions):
        return True
    return any(any(part.lower().endswith(ext) for ext in blocked_extensions) for part in path.parts)


def check_paths(paths: list[Path], policy: dict[str, Any], *, root: Path) -> list[str]:
    max_bytes = int(float(policy.get("max_file_size_mb", 10)) * 1024 * 1024)
    blocked_extensions = {ext.lower() for ext in policy.get("blocked_extensions", [])}
    blocked_paths = list(policy.get("blocked_paths", []))
    allowed_paths = list(policy.get("allowed_paths", []))

    errors: list[str] = []
    for path in paths:
        full_path = root / path
        if not full_path.exists() or full_path.is_dir():
            continue
        if _is_under(path, allowed_paths):
            continue
        if _has_blocked_extension(path, blocked_extensions):
            errors.append(f"{path}: blocked generated-data extension")
        if _is_under(path, blocked_paths):
            errors.append(f"{path}: blocked generated-data path")
        size = full_path.stat().st_size
        if size > max_bytes:
            size_mb = size / 1024 / 1024
            errors.append(f"{path}: {size_mb:.1f} MB exceeds {policy.get('max_file_size_mb', 10)} MB")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default="config/repository_policy.yml")
    parser.add_argument("--mode", choices=("tracked", "staged"), default="tracked")
    args = parser.parse_args(argv)

    root = Path.cwd()
    policy = _load_policy(root / args.policy)
    paths = _git_files(args.mode)
    errors = check_paths(paths, policy, root=root)
    if errors:
        print("Repository size policy failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"Repository size policy passed for {len(paths)} {args.mode} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
