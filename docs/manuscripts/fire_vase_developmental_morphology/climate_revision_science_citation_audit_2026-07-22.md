# Climate Revision Science-Style Citation Audit

Date: 2026-07-22

Object reviewed:
`docs/manuscripts/fire_vase_developmental_morphology/manuscript_climate_revision_science_style.md`
and `output/pdf/fire_vase_climate_revision_science_style_manuscript.pdf`.

## Summary

The climate-revision manuscript now uses numbered Science-style citations in
order of first appearance. Every in-text citation resolves to a reference, and
every reference is cited. References that belonged to older drafts but did not
support claims in this climate-revision narrative were removed.

The manuscript argument is now supported by four citation groups:

- Climate and fire-growth motivation: warming, aridity, VPD, and fast growth.
- Data provenance: MODIS burned area, FIRED event products, country-level
  perimeter products, and gridMET climate.
- Method framing: morphometrics, functional data analysis, PCA, human ignition
  context, and spatially explicit daily fire progression.
- Landscape controls: environmental controls on wildfire distribution, fuels
  and topography as constraints on spread/boundaries, and scale-dependent
  topographic control.

## Reference Checks

| Ref. | Source checked | Claim supported in manuscript | Status |
| --- | --- | --- | --- |
| 1. Westerling et al. 2006, Science, doi:10.1126/science.1128834 | PubMed bibliographic page | Warming and earlier spring conditions are associated with western U.S. wildfire activity. | Real; appropriate. |
| 2. Abatzoglou and Williams 2016, PNAS, doi:10.1073/pnas.1607171113 | DOI/bibliographic record | Anthropogenic climate change has increased wildfire potential across western U.S. forests. | Real; appropriate. |
| 3. Williams et al. 2019, Earth's Future, doi:10.1029/2019EF001210 | NOAA/Wiley bibliographic pages | Warming, atmospheric aridity, and dry fuels contribute to California wildfire activity. | Real; appropriate. |
| 4. Balch et al. 2024, Science, doi:10.1126/science.adk5737 | University bibliographic page | Fast-growing fires motivate analysis of daily growth histories rather than final size alone. | Real; appropriate. |
| 5. Giglio et al. 2018, Remote Sensing of Environment, doi:10.1016/j.rse.2018.08.005 | University/PMC bibliographic pages | MODIS Collection 6 burned-area mapping is the satellite burned-area basis. | Real; appropriate. |
| 6. Balch et al. 2020, Remote Sensing, doi:10.3390/rs12213498 | University bibliographic page | FIRED event delineation and database derived from MODIS burned area. | Real; appropriate. |
| 7. Mahood et al. 2022, Scientific Data, doi:10.1038/s41597-022-01572-3 | NOAA/CU bibliographic pages | Country-level fire perimeter/event data and FIREDpy-derived perimeter products. | Real; appropriate. |
| 8. Abatzoglou 2013, International Journal of Climatology, doi:10.1002/joc.3413 | Wiley article page | gridMET-style high-resolution daily gridded meteorological data for ecological applications. | Real; appropriate. |
| 9. Bookstein 1991, Cambridge University Press | Google Books/Cambridge/Open Library records | Morphometric framing for representing biological or developmental form in geometric space. | Real; appropriate as conceptual method citation. |
| 10. Ramsay and Silverman 2005, Springer, doi:10.1007/b98888 | Springer book page | Functional data analysis as a framework for comparing curves or histories. | Real; appropriate. |
| 11. Jolliffe 2002, Springer, doi:10.1007/b98835 | Springer book page | PCA/dimension reduction method context. | Real; appropriate. |
| 12. Balch et al. 2017, PNAS, doi:10.1073/pnas.1617394114 | PNAS/PubMed pages | Human ignitions reshape the spatial and seasonal fire niche and motivate ignition context as a missing control. | Real; appropriate. |
| 13. Veraverbeke et al. 2014, International Journal of Wildland Fire, doi:10.1071/WF13015 | University bibliographic page | Daily fire progression can require spatially explicit active-fire/growth tracking. | Real; appropriate. |
| 14. Parisien and Moritz 2009, Ecological Monographs, doi:10.1890/07-1289.1 | Wiley article page | Environmental controls on wildfire distribution vary across scales and help explain transfer limits. | Real; appropriate. |
| 15. Holsinger et al. 2016, Forest Ecology and Management, doi:10.1016/j.foreco.2016.08.035 | U.S. Forest Service bibliographic page | Weather, fuels, and topography can impede fire spread and form fire boundaries. | Real; appropriate. |
| 16. Povak et al. 2018, Ecosphere, doi:10.1002/ecs2.2443 | Wiley/EPA bibliographic pages | Topographic controls on wildfire spread are scale dependent. | Real; appropriate. |

## Citation Integrity Checks

- In-text citations found: `(1-3)`, `(4)`, `(5-7)`, `(8)`, `(9-11)`,
  `(1-3)`, `(12)`, `(13)`, `(14-16)`.
- References cited: 1 through 16.
- Uncited references: none.
- Missing references: none.
- Abstract citations: none.
- Claims about causality, suppression, fuels, active-edge exposure, wind
  direction, and local normals are framed as limitations or future data needs,
  not as completed results.

## Remaining Pre-Submission Citation Tasks

- Replace repository placeholders with a persistent public code/data archive.
- Add final author, affiliation, funding, contribution, and competing-interest
  metadata.
- Decide whether the supplementary methods need separate citations for ridge
  regression, blocked validation, and any final software packages once the
  final supplement is drafted.
