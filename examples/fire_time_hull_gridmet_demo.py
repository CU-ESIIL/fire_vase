"""
Example: Fire time-hull × GRIDMET climate using cubedynamics

This example assumes:
  - Network access to CU Scholar and GRIDMET.
  - FIRED and GRIDMET servers are reachable.

It is not run in automated tests.
"""

import pandas as pd

import cubedynamics as cd
from cubedynamics import pipe, verbs as v


def main():
    fired_evt = cd.fired_event(event_id=21281)

    start = fired_evt.t0 - pd.Timedelta(days=14)
    end = fired_evt.t1 + pd.Timedelta(days=14)

    clim = cd.gridmet(
        lat=fired_evt.centroid_lat,
        lon=fired_evt.centroid_lon,
        start=str(start.date()),
        end=str(end.date()),
        variable="tmmx",
    )

    # Quiet, hull-only visualization (default): extract + 3D vase
    pipe(clim) | v.fire_plot(fired_event=fired_evt)

    # Opt-in diagnostics and histogram
    pipe(clim) | v.fire_plot(
        fired_event=fired_evt,
        show_hist=True,
        verbose=True,
    )

    # Panel access: receive figures for custom layouts
    out, fig_vase, fig_hist = v.fire_panel(
        clim,
        fired_event=fired_evt,
        bins=40,
    )
    print("Vase figure:", type(fig_vase))
    print("Histogram figure:", type(fig_hist))

    # Inspect metadata attached by v.extract (called inside fire_panel)
    base_da = out if not hasattr(out, "data") else out.data
    print("attrs keys:", base_da.attrs.keys())
    hull = base_da.attrs.get("fire_time_hull")
    summary = base_da.attrs.get("fire_climate_summary")
    print("Hull metrics:", getattr(hull, "metrics", None))
    per_day_mean = getattr(summary, "per_day_mean", None)
    if per_day_mean is not None:
        print("Per-day mean climate (head):")
        print(per_day_mean.head())


if __name__ == "__main__":
    main()
