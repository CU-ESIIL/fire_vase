"""One-to-one event matching helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd


def parse_tolerance(value: str | int | None) -> np.timedelta64:
    """Parse day/year tolerances used by event synchrony verbs."""

    if value is None:
        return np.timedelta64(0, "D")
    if isinstance(value, int):
        return np.timedelta64(value, "D")
    text = value.strip().upper()
    if text.endswith("D"):
        return np.timedelta64(int(text[:-1]), "D")
    if text.endswith("Y"):
        return np.timedelta64(int(text[:-1]) * 365, "D")
    raise ValueError("tolerance strings must use 'D' or 'Y', e.g. '7D'")


def match_events(
    source: pd.DataFrame,
    target: pd.DataFrame,
    *,
    anchor: str = "start",
    tolerance: str | int | None = "7D",
) -> pd.DataFrame:
    """Greedily match events one-to-one within a time tolerance."""

    if anchor not in {"start", "end", "peak"}:
        raise ValueError("anchor must be 'start', 'peak', or 'end'")
    if anchor == "peak":
        anchor = "start"
    tol = parse_tolerance(tolerance)
    if source.empty or target.empty:
        return pd.DataFrame()
    candidates = []
    used_columns = ["event_id", "start", "end", "duration"]
    src = source[used_columns].copy()
    tgt = target[used_columns].copy()
    src_anchor = pd.to_datetime(src[anchor])
    tgt_anchor = pd.to_datetime(tgt[anchor])
    for i, s_row in src.iterrows():
        for j, t_row in tgt.iterrows():
            lag = tgt_anchor.loc[j].to_datetime64() - src_anchor.loc[i].to_datetime64()
            if abs(lag) <= tol:
                candidates.append(
                    {
                        "source_event_id": s_row["event_id"],
                        "target_event_id": t_row["event_id"],
                        "source_start": s_row["start"],
                        "target_start": t_row["start"],
                        "source_end": s_row["end"],
                        "target_end": t_row["end"],
                        "source_duration": s_row["duration"],
                        "target_duration": t_row["duration"],
                        "lag_days": float(lag / np.timedelta64(1, "D")),
                        "abs_lag_days": float(abs(lag) / np.timedelta64(1, "D")),
                    }
                )
    if not candidates:
        return pd.DataFrame()
    candidate_df = pd.DataFrame(candidates).sort_values(["abs_lag_days", "source_event_id", "target_event_id"])
    matched = []
    used_source: set[object] = set()
    used_target: set[object] = set()
    for _, row in candidate_df.iterrows():
        if row["source_event_id"] in used_source or row["target_event_id"] in used_target:
            continue
        matched.append(row.to_dict())
        used_source.add(row["source_event_id"])
        used_target.add(row["target_event_id"])
    return pd.DataFrame(matched)
