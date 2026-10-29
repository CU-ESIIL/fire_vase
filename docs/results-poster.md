# Fire VASE results poster

The [24 x 36 inch portrait poster](../output/pdf/fire_vase_results_poster.pdf)
showcases the data-derived vase for western-region fire 387635 (2018) and
current v2 Figures 1 and 2. It emphasizes developmental representation and
continuous gradients rather than discrete fire classes or causal weather claims.

The hero uses the existing `scripts/generate_hero_vase.py` rendering and the
local data-lake slices, rendered at 650 dpi before transparent-margin cropping.
The white-background design uses soft vector cast and contact shadows beneath
the vase and subtle shadows beneath the figure panels. The final placement is 401 dpi; typography and the two original
scientific PDF panels remain vector artwork. Print at actual size (24 x 36
inches); the design includes internal margins and requires no bleed.

## Rebuild

Run `python scripts/build_results_poster.py` with ReportLab, pypdf and Pillow.
The default uses the preserved website hero; supply `--hero path/to/hero.png`
for a higher-resolution render of the same event. The script currently uses
macOS Arial fonts in `/System/Library/Fonts/Supplemental/`.

Sources are `docs/assets/hero-vase-vpd.json`, the corresponding hero PNG,
`figures/v2/Figure_1.pdf`, `figures/v2/Figure_2.pdf`, and their figure legends.
No external images or data were introduced. The hero is an illustrative,
smoothed surface of normalized cumulative growth; its weather colours describe
daily centroid gridMET vapour pressure deficit. It is not a causal model.

Verification: rendered the completed one-page PDF for visual inspection and
checked page size and embedded text. No analysis results were recomputed.

The bottom-right panel is a simplified PCA map rendered from unchanged
`analysis/v2/event_analysis.parquet` scores by `scripts/render_poster_pca.py`.
It shows only the two leading axes, explains their developmental meaning, and
labels density as fires per hexagon. Together these axes explain 62.4% of
variation. The builder calls the repository `.venv/bin/python` for this helper
(matplotlib, pandas and pyarrow required). The original Figure 2 is unchanged.

The PCA density layer is rasterized at 450 dpi to avoid negative-coordinate
hexagon clipping in the local PDF renderer; its labels and axes remain vector.
