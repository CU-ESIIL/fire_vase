# Manuscript–SI consistency report

## Result

**PASS.** The supplied 22-page manuscript and 22-page SI were treated as the editorial text sources. Analytical numbers were checked against the 798-row validated headline crosswalk, the compositional sensitivity tables, and the final adversarial tables; the machine-readable union contains 1,005 registered value/source records.

| check | pass | evidence |
| --- | --- | --- |
| Source manuscript identity | True | c3704f30ce60e948b8463f4c9f8e81e3b07e55e729305e845957b544b672a323 |
| Source SI identity | True | 4097371d75eda8572c38d2d5d501c5486e34074a57d5c891da5c5877349f2566 |
| Final manuscript pages | True | 27 |
| Final SI pages | True | 26 |
| Placeholder/obsolete machine-text scan | True | none |
| Retired numeric headline scan | True | none |
| Registered claim sources | True | 1005 |
| Full test collection | True | 152 passed, 2 skipped, 125 warnings; no collection exclusions |
| Visual PDF audit | True | all 27 manuscript, 26 SI, and 1 adversarial-figure pages rendered; edited/full-figure pages inspected at full resolution |

## Rounding and scope

- Prose values are permitted to round the authoritative table value to the displayed digits (usually three decimals, one decimal percentage point, or whole counts). SI tables retain more digits. This is not a discrepancy.
- Bibliographic years, equation indices, section/page/line numbers, and fixed protocol constants are not inferential result claims. Protocol constants are controlled by `config/analysis_v2.json` and the Methods.
- Main and SI cohort labels agree: 10,246 primary histories, 9,212 complete event-weather fires, and a distinct 87,944-transition/31,700-fire state cohort.
- The retired 81.0%/96.3% PCA headlines and the invalid 0.349 aggregate weather headline do not occur in the supplied current drafts.
- The apparent phrase “excess mismatch” occurs only in the explicitly negative statement “No excess mismatch was detected”; the positive claim remains retired.
- Post-draft adversarial depth and boundary estimates are handed off in `PRISM_HANDOFF_FINAL_ADVERSARIAL.md` rather than silently rewritten into the supplied manuscript, as requested.

## PDF assembly

Each visible placeholder was replaced with the matching repository asset. A full-size vector figure page follows each dense thumbnail. Only the edited source text pages were flattened at 300 dpi to remove hidden obsolete placeholder/provenance text; all unedited text pages and full-size figure pages remain vector PDF. Machine scans of the final files find no placeholder instructions, obsolete baseline SHA, or missing-helper language.
