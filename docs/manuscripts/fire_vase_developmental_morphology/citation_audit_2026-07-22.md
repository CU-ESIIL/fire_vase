# Citation Audit

Date: 2026-07-22

Object reviewed: `output/pdf/fire_vase_developmental_morphology_manuscript.pdf`
and `scripts/fire_vase_science_manuscript_pdf.py`.

## Summary

The original references were real and broadly relevant, but several placements
were overloaded. In particular, the opening sentence cited FIRED, country-level
perimeters, and gridMET without separately citing the MODIS burned-area product
that underlies the event histories. The manuscript also used morphospace,
principal component analysis, bootstrap stability, and farthest-point medoid
coverage without method citations.

This round added or repositioned citations so that:
- MODIS burned-area mapping is cited directly.
- FIRED and country-level fire-perimeter/event products are cited separately.
- gridMET supports the climate-data source.
- Fire-climate, VPD, fast growth, fuels, topography, and human ignition claims
  are supported by more specific wildfire literature.
- Morphospace/geometric-morphometric framing is explicitly cited.
- PCA, bootstrap resampling, and farthest-point coverage are cited as methods.

## Existing Citation Checks

| Original reference | Status | Fit to manuscript claim | Action |
| --- | --- | --- | --- |
| Balch et al. 2020, FIRED, Remote Sensing 12, 3498 | Real. DOI verified: `10.3390/rs12213498`. | Appropriate for fire event delineation from MODIS burned area. | Retained, moved to reference 2. |
| Mahood et al. 2022, Scientific Data 9, 458 | Real. DOI verified: `10.1038/s41597-022-01572-3`. | Appropriate for country-level event perimeter datasets and FIREDpy-derived perimeters. | Retained, moved to reference 3. |
| Abatzoglou 2013, International Journal of Climatology 33, 121-131 | Real. DOI verified: `10.1002/joc.3413`. | Best citation for gridMET-style gridded meteorological data used for ecological applications. | Retained, moved to reference 4. |
| Abatzoglou and Williams 2016, PNAS 113, 11770-11775 | Real. DOI verified: `10.1073/pnas.1607171113`. | Appropriate for anthropogenic climate, fuel aridity, and western U.S. forest fire area. | Retained, moved to reference 5. |
| Williams et al. 2019, Earth's Future 7, 892-910 | Real. DOI verified: `10.1029/2019EF001210`. | Appropriate for warming-driven fuel drying and California wildfire activity. | Retained, moved to reference 6. |
| He et al. 2025, Geophysical Research Letters 52, e2024GL113708 | Real. DOI verified: `10.1029/2024GL113708`. | Appropriate for VPD calculation sensitivity and fire-VPD relationships. | Retained, moved to reference 7. |
| Balch et al. 2024, Science 386, 425-431 | Real. DOI verified: `10.1126/science.adk5737`. | Strong support for the importance of daily fire growth and fast-spreading fires. | Retained, moved to reference 8. |
| Holsinger et al. 2016, Forest Ecology and Management 380, 59-69 | Real. DOI verified: `10.1016/j.foreco.2016.08.035`. | Strong support for weather, fuels, and topography impeding fire spread. | Retained, moved to reference 9. |
| Povak et al. 2018, Ecosphere 9, e02443 | Real. DOI verified: `10.1002/ecs2.2443`. | Strong support for scale-dependent topographic controls on wildfire spread. | Retained, moved to reference 10. |
| Bookstein 1991 | Real book; bibliographic record verified. | Appropriate background for morphometric coordinate systems, but it was previously uncited. | Retained, moved to reference 13 and cited in the Introduction. |
| Mitteroecker and Gunz 2009, Evolutionary Biology 36, 235-247 | Real. DOI verified: `10.1007/s11692-009-9055-x`. | Appropriate background for geometric morphometrics and shape/form spaces, but it was previously uncited. | Retained, moved to reference 14 and cited in the Introduction. |

## Added Citations

| Added reference | Why added |
| --- | --- |
| Giglio et al. 2018, Remote Sensing of Environment 217, 72-85, `10.1016/j.rse.2018.08.005` | Direct citation for the MODIS Collection 6 burned-area mapping algorithm and product. This is a better source for "satellite burned-area products map burned pixels" than FIRED alone. |
| Balch et al. 2017, PNAS 114, 2946-2951, `10.1073/pnas.1617394114` | Supports the claim that human activity and ignition context influence U.S. fire regimes. |
| Foote 1997, Annual Review of Ecology and Systematics 28, 129-152, `10.1146/annurev.ecolsys.28.1.129` | A clearer morphospace citation for the idea that complex forms can be compared in morphological spaces. |
| Jolliffe and Cadima 2016, Philosophical Transactions of the Royal Society A 374, 20150202, `10.1098/rsta.2015.0202` | Supports the PCA dimensionality-reduction method. |
| Gonzalez 1985, Theoretical Computer Science 38, 293-306, `10.1016/0304-3975(85)90224-5` | Supports farthest-point/k-center coverage logic used for representative medoid selection. |
| Efron and Tibshirani 1993, An Introduction to the Bootstrap | Supports bootstrap resampling for PCA stability intervals. |

## Places That Needed Citations

| Manuscript location | Issue | Citation response |
| --- | --- | --- |
| Introduction, opening sentence | Satellite burned-area mapping was not directly cited. | Added Giglio et al. 2018. |
| Introduction, morphospace framing | Morphospace/geometric morphometrics were referenced conceptually but not cited in text. | Added Foote 1997, Bookstein 1991, and Mitteroecker and Gunz 2009. |
| Methods, PCA | PCA was used without a methodological citation. | Added Jolliffe and Cadima 2016. |
| Methods, farthest-point medoid coverage | Representative selection used farthest-point logic without a method citation. | Added Gonzalez 1985. |
| Methods, bootstrap resampling | Bootstrap stability intervals were reported without a bootstrap citation. | Added Efron and Tibshirani 1993. |
| Introduction, human activity/ignition | Existing climate and topography citations did not directly support human activity. | Added Balch et al. 2017. |

## Remaining Citation Caveats

- The manuscript still cites placeholder internal workflow outputs for the
  Fire VASE analysis itself. Before submission, these outputs should be paired
  with a public repository, DOI, or supplementary data archive.
- The reference list now includes method citations, but the manuscript does
  not yet include a formal software/data availability citation for
  CubeDynamics.
- Climate statements remain appropriately cautious because current
  manuscript-scale attribution is centroid-based.
