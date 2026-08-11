# Prediction Section Decision

## Recommendation

**C. Move the fixed-day prediction analysis to the supplement as a leakage audit and benchmark.**

The current fixed-day benchmark is scientifically useful because it prevents overstating early prediction, but it is too weak and confusing to close the main paper. The main manuscript should not end on near-zero or negative blocked R2 unless the negative result becomes the paper's central finding.

## Current Blocked Prediction Summary

| stage | stage_order | model | n_folds | mean_r2 | lo_r2 | hi_r2 | n_test_total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| day 1 | 1 | climate only | 27 | 0.0003 | -0.0125 | 0.0081 | 1423410 |
| day 1 | 1 | geometry + climate | 27 | 0.0179 | -0.0354 | 0.0869 | 1423410 |
| day 1 | 1 | geometry only | 30 | 0.0079 | -0.0879 | 0.0815 | 1671414 |
| day 1 | 1 | trivial stage summary | 30 | 0.0078 | -0.0883 | 0.0817 | 1671414 |
| day 2 | 2 | climate only | 27 | 0.0021 | -0.0148 | 0.0178 | 634410 |
| day 2 | 2 | geometry + climate | 27 | 0.0205 | -0.0184 | 0.1038 | 634410 |
| day 2 | 2 | geometry only | 30 | 0.0097 | -0.0988 | 0.0964 | 704976 |
| day 2 | 2 | trivial stage summary | 30 | 0.0101 | -0.0987 | 0.0967 | 704976 |
| day 4 | 4 | climate only | 27 | 0.0085 | -0.0172 | 0.0380 | 249798 |
| day 4 | 4 | geometry + climate | 27 | 0.0229 | -0.0050 | 0.0948 | 249798 |
| day 4 | 4 | geometry only | 30 | -0.0107 | -0.1994 | 0.0823 | 271170 |
| day 4 | 4 | trivial stage summary | 30 | -0.0144 | -0.2042 | 0.0707 | 271170 |
| day 8 | 8 | climate only | 27 | 0.0147 | -0.0535 | 0.0789 | 58044 |
| day 8 | 8 | geometry + climate | 27 | 0.0359 | -0.0331 | 0.1456 | 58044 |
| day 8 | 8 | geometry only | 27 | 0.0203 | -0.0816 | 0.1283 | 64896 |
| day 8 | 8 | trivial stage summary | 27 | 0.0196 | -0.0460 | 0.1048 | 64896 |

## Suggested Alternatives For Later

- Predict final-size quantile or developmental neighborhood rather than continuous PC1-PC3.
- Use strict spatial-temporal blocking with simple regularized regression and one nonlinear baseline.
- Try analog prediction from nearest partial-history neighbors.
- Predict future growth allocation or transition direction once a genuine dynamic state-space test is implemented.
