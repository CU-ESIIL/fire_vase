"""Plot preserved legacy fuel-moisture associations; no new inference."""
from pathlib import Path
import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "analysis/climate_revision_stats/climate_response_spearman_effects.csv"
OUT = ROOT / "figures/exploratory/fuel_moisture_associations"
RESPONSES = {
    "front_loaded_fraction": "Early growth fraction",
    "late_growth_fraction": "Late growth fraction",
    "terminal_taper_fraction": "Terminal taper fraction",
    "growth_entropy": "Growth entropy",
    "pulse_count": "Pulse count",
    "peak_timing": "Peak timing",
}

def main():
    with SOURCE.open() as stream:
        rows = list(csv.DictReader(stream))
    fig, ax = plt.subplots(figsize=(9, 5.6))
    for suffix, label, color, offset in [
        ("100hr", "100-hour dead fuel moisture", "#227c9d", -.13),
        ("1000hr", "1000-hour dead fuel moisture", "#b65d30", .13),
    ]:
        values = []
        for response in RESPONSES:
            matches = [r for r in rows if r["response"] == response and
                       r["predictor"] == f"mean_fuel_moisture_{suffix}_pct"]
            assert len(matches) == 1
            assert int(matches[0]["n"]) == 237235
            values.append(float(matches[0]["spearman_rho"]))
        ys = [i + offset for i in range(len(values))]
        ax.scatter(values, ys, color=color, s=55, label=label, zorder=3)
        for x, y in zip(values, ys):
            ax.annotate(f"{x:+.3f}", (x, y), xytext=(7, 0),
                        textcoords="offset points", va="center", fontsize=9, color=color)
    ax.axvline(0, color="#555555", lw=1)
    ax.set(xlim=(-1, 1), yticks=range(len(RESPONSES)),
           yticklabels=list(RESPONSES.values()),
           xlabel="Spearman correlation (ρ; full possible range)")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=.15)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), frameon=False, fontsize=10)
    fig.suptitle("Dead fuel moisture: very small associations with VASE traits",
                 x=.04, ha="left", fontsize=15, weight="bold")
    fig.text(.04, .035,
             "Preserved legacy analysis • 237,235 fires • event-mean centroid exposures\n"
             "Small effect sizes, not evidence of zero effect; all plotted nominal p < 0.05.\n"
             "Unadjusted associations; these are not corrected v2 shape-only results.",
             fontsize=9, color="#555555", linespacing=1.5)
    fig.subplots_adjust(left=.26, right=.96, bottom=.24, top=.79)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        fig.savefig(OUT.with_suffix(f".{ext}"), dpi=220, facecolor="white")
    plt.close(fig)

if __name__ == "__main__":
    main()
