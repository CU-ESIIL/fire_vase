#!/usr/bin/env python3
"""Render all manuscript figures into this folder."""

from __future__ import annotations

import json

from _figure_runner import build_parser, render_all


def main() -> int:
    args = build_parser(__doc__).parse_args()
    outputs = render_all(args)
    print(json.dumps(outputs, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
