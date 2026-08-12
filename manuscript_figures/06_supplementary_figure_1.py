#!/usr/bin/env python3
"""Render Supplementary Figure 1 validation summaries into this folder."""

from __future__ import annotations

import json

from _figure_runner import build_parser, render_supplementary


def main() -> int:
    args = build_parser(__doc__).parse_args()
    print(json.dumps(render_supplementary(args), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
