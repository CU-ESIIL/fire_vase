# PC1 Robustness Report

Random seed: `20260722`.

## Interpretation

PC1 is not simply final burned area or duration. Removing final area, scale variables, and duration/observation count does not eliminate low-dimensionality. However, PC1 is strongly shaped by cumulative-width and growth-profile features, and those features contain monotone and duplicated information by design. The honest interpretation is that PC1 is primarily a dominant **developmental profile / allocation axis**, not a pure mechanistic axis.

## PCA Ablations

| feature_set | n_fires | n_features | pc1 | pc2 | pc3 | pc4 | pc5 | cumvar_pc1_5 | subspace_overlap_to_full_pc1_5 | recognizable_gradients_remain |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full current feature set | 278569 | 36 | 0.8099 | 0.0664 | 0.0354 | 0.0330 | 0.0180 | 0.9627 | 1.0000 | yes |
| scale variables removed | 278569 | 33 | 0.8380 | 0.0632 | 0.0376 | 0.0243 | 0.0094 | 0.9725 | 0.8112 | yes |
| final area removed | 278569 | 35 | 0.8150 | 0.0638 | 0.0360 | 0.0325 | 0.0182 | 0.9655 | 0.9999 | yes |
| duration and observation count removed | 278569 | 34 | 0.8110 | 0.0648 | 0.0361 | 0.0339 | 0.0189 | 0.9648 | 0.9998 | yes |
| all scale and duration variables removed | 278569 | 31 | 0.8414 | 0.0608 | 0.0380 | 0.0258 | 0.0096 | 0.9756 | 0.8002 | yes |
| normalized profile variables only | 278569 | 22 | 0.9246 | 0.0471 | 0.0171 | 0.0051 | 0.0021 | 0.9960 | 0.8443 | yes |
| growth-share profile only | 278569 | 11 | 0.9745 | 0.0156 | 0.0059 | 0.0022 | 0.0009 | 0.9991 | 0.9887 | yes |
| cumulative-width profile only | 278569 | 11 | 0.9346 | 0.0492 | 0.0099 | 0.0033 | 0.0014 | 0.9985 | 0.7962 | yes |
| pulse timing taper entropy shape variables only | 278569 | 9 | 0.6327 | 0.1692 | 0.0961 | 0.0540 | 0.0261 | 0.9782 | 0.9471 | yes |
| one representative per correlated cluster | 278569 | 11 | 0.5844 | 0.1581 | 0.0938 | 0.0698 | 0.0400 | 0.9460 | 0.9883 | yes |
| interpolated profile features removed | 278569 | 14 | 0.6131 | 0.1483 | 0.0911 | 0.0567 | 0.0363 | 0.9455 | 0.9922 | yes |
| summary features removed retaining profiles | 278569 | 22 | 0.9246 | 0.0471 | 0.0171 | 0.0051 | 0.0021 | 0.9960 | 0.8443 | yes |
| profiles normalized independently of final size | 278569 | 22 | 0.9246 | 0.0471 | 0.0171 | 0.0051 | 0.0021 | 0.9960 | 0.8443 | yes |
| full current feature set, duration >= 2 days | 117496 | 36 | 0.4207 | 0.2623 | 0.0913 | 0.0633 | 0.0415 | 0.8790 | 0.7736 | yes, but redistributed |
| full current feature set, duration >= 4 days | 81730 | 36 | 0.3827 | 0.2606 | 0.1068 | 0.0620 | 0.0527 | 0.8648 | 0.7559 | yes, but redistributed |
| full current feature set, duration >= 8 days | 31330 | 36 | 0.2794 | 0.2561 | 0.1331 | 0.0894 | 0.0554 | 0.8134 | 0.6683 | yes, but redistributed |
| full current feature set, duration >= 10 days | 19528 | 36 | 0.2777 | 0.2553 | 0.1340 | 0.0667 | 0.0509 | 0.7846 | 0.5823 | yes, but redistributed |

## PC1 Correlations

| feature_set | pc1_target | pearson_r |
| --- | --- | --- |
| all scale and duration variables removed | log_duration_days | -0.9340 |
| all scale and duration variables removed | growth_entropy | -0.9188 |
| all scale and duration variables removed | log_final_area_km2 | -0.8033 |
| all scale and duration variables removed | late_growth_fraction | -0.7905 |
| all scale and duration variables removed | observation_count | -0.7049 |
| all scale and duration variables removed | log_peak_growth_km2_per_day | -0.1962 |
| all scale and duration variables removed | terminal_taper_fraction | 0.5988 |
| all scale and duration variables removed | width_p05 | 0.9293 |
| all scale and duration variables removed | front_loaded_fraction | 0.9508 |
| all scale and duration variables removed | growth_p05 | 0.9587 |
| cumulative-width profile only | log_duration_days | -0.8555 |
| cumulative-width profile only | growth_entropy | -0.8433 |
| cumulative-width profile only | late_growth_fraction | -0.8247 |
| cumulative-width profile only | log_final_area_km2 | -0.7223 |
| cumulative-width profile only | observation_count | -0.6424 |
| cumulative-width profile only | log_peak_growth_km2_per_day | -0.1558 |
| cumulative-width profile only | terminal_taper_fraction | 0.4339 |
| cumulative-width profile only | growth_p05 | 0.8833 |
| cumulative-width profile only | width_p05 | 0.9769 |
| cumulative-width profile only | front_loaded_fraction | 0.9820 |
| duration >= 10 days | log_final_area_km2 | -0.8736 |
| duration >= 10 days | observation_count | -0.8315 |
| duration >= 10 days | log_peak_growth_km2_per_day | -0.7916 |
| duration >= 10 days | log_duration_days | -0.6501 |
| duration >= 10 days | front_loaded_fraction | 0.0579 |
| duration >= 10 days | width_p05 | 0.0660 |
| duration >= 10 days | growth_entropy | 0.3522 |
| duration >= 10 days | growth_p05 | 0.3615 |
| duration >= 10 days | late_growth_fraction | 0.3758 |
| duration >= 10 days | terminal_taper_fraction | 0.6286 |
| duration >= 2 days | log_duration_days | -0.7642 |
| duration >= 2 days | observation_count | -0.7568 |
| duration >= 2 days | log_final_area_km2 | -0.7187 |
| duration >= 2 days | log_peak_growth_km2_per_day | -0.3926 |
| duration >= 2 days | late_growth_fraction | 0.1514 |
| duration >= 2 days | growth_entropy | 0.2241 |
| duration >= 2 days | terminal_taper_fraction | 0.3271 |
| duration >= 2 days | width_p05 | 0.6866 |
| duration >= 2 days | front_loaded_fraction | 0.7249 |
| duration >= 2 days | growth_p05 | 0.7359 |
| duration >= 4 days | observation_count | -0.7719 |
| duration >= 4 days | log_final_area_km2 | -0.7568 |
| duration >= 4 days | log_duration_days | -0.7378 |
| duration >= 4 days | log_peak_growth_km2_per_day | -0.5710 |
| duration >= 4 days | late_growth_fraction | 0.1566 |
| duration >= 4 days | growth_entropy | 0.2508 |
| duration >= 4 days | terminal_taper_fraction | 0.3863 |
| duration >= 4 days | width_p05 | 0.6107 |
| duration >= 4 days | front_loaded_fraction | 0.6380 |
| duration >= 4 days | growth_p05 | 0.6852 |
| duration >= 8 days | observation_count | -0.7004 |
| duration >= 8 days | log_final_area_km2 | -0.6188 |
| duration >= 8 days | log_duration_days | -0.6163 |
| duration >= 8 days | log_peak_growth_km2_per_day | -0.5043 |
| duration >= 8 days | late_growth_fraction | -0.2546 |
| duration >= 8 days | growth_entropy | 0.1438 |
| duration >= 8 days | terminal_taper_fraction | 0.1884 |
| duration >= 8 days | growth_p05 | 0.4502 |
| duration >= 8 days | width_p05 | 0.6629 |
| duration >= 8 days | front_loaded_fraction | 0.6632 |
| duration and observation count removed | log_duration_days | -0.9391 |
| duration and observation count removed | growth_entropy | -0.9172 |
| duration and observation count removed | log_final_area_km2 | -0.8123 |
| duration and observation count removed | late_growth_fraction | -0.7826 |
| duration and observation count removed | observation_count | -0.7134 |
| duration and observation count removed | log_peak_growth_km2_per_day | -0.2055 |
| duration and observation count removed | terminal_taper_fraction | 0.6094 |
| duration and observation count removed | width_p05 | 0.9256 |
| duration and observation count removed | front_loaded_fraction | 0.9477 |
| duration and observation count removed | growth_p05 | 0.9606 |
| final area removed | log_duration_days | -0.9453 |
| final area removed | growth_entropy | -0.9163 |
| final area removed | log_final_area_km2 | -0.8129 |
| final area removed | late_growth_fraction | -0.7751 |
| final area removed | observation_count | -0.7264 |
| final area removed | log_peak_growth_km2_per_day | -0.1985 |
| final area removed | terminal_taper_fraction | 0.6150 |
| final area removed | width_p05 | 0.9230 |
| final area removed | front_loaded_fraction | 0.9459 |
| final area removed | growth_p05 | 0.9621 |
| full current feature set | log_duration_days | -0.9468 |
| full current feature set | growth_entropy | -0.9139 |
| full current feature set | log_final_area_km2 | -0.8214 |
| full current feature set | late_growth_fraction | -0.7696 |
| full current feature set | observation_count | -0.7319 |
| full current feature set | log_peak_growth_km2_per_day | -0.2115 |
| full current feature set | terminal_taper_fraction | 0.6224 |
| full current feature set | width_p05 | 0.9207 |
| full current feature set | front_loaded_fraction | 0.9436 |
| full current feature set | growth_p05 | 0.9627 |
| growth-share profile only | log_duration_days | -0.9617 |
| growth-share profile only | growth_entropy | -0.9305 |
| growth-share profile only | log_final_area_km2 | -0.8386 |
| growth-share profile only | observation_count | -0.7372 |
| growth-share profile only | late_growth_fraction | -0.6950 |
| growth-share profile only | log_peak_growth_km2_per_day | -0.2225 |
| growth-share profile only | terminal_taper_fraction | 0.7122 |
| growth-share profile only | width_p05 | 0.8387 |
| growth-share profile only | front_loaded_fraction | 0.8750 |
| growth-share profile only | growth_p05 | 0.9838 |
| interpolated profile features removed | log_duration_days | -0.9530 |
| interpolated profile features removed | growth_entropy | -0.8899 |
| interpolated profile features removed | log_final_area_km2 | -0.8495 |
| interpolated profile features removed | observation_count | -0.7769 |
| interpolated profile features removed | late_growth_fraction | -0.7387 |
| interpolated profile features removed | log_peak_growth_km2_per_day | -0.2535 |
| interpolated profile features removed | terminal_taper_fraction | 0.6687 |
| interpolated profile features removed | width_p05 | 0.8908 |
| interpolated profile features removed | front_loaded_fraction | 0.9136 |
| interpolated profile features removed | growth_p05 | 0.9428 |
| normalized profile variables only | log_duration_days | -0.9397 |
| normalized profile variables only | growth_entropy | -0.9156 |
| normalized profile variables only | log_final_area_km2 | -0.8090 |
| normalized profile variables only | late_growth_fraction | -0.7734 |
| normalized profile variables only | observation_count | -0.7150 |
| normalized profile variables only | log_peak_growth_km2_per_day | -0.1989 |
| normalized profile variables only | terminal_taper_fraction | 0.6045 |
| normalized profile variables only | width_p05 | 0.9257 |
| normalized profile variables only | front_loaded_fraction | 0.9486 |
| normalized profile variables only | growth_p05 | 0.9645 |
| one representative per correlated cluster | log_duration_days | -0.9329 |
| one representative per correlated cluster | log_final_area_km2 | -0.9111 |
| one representative per correlated cluster | observation_count | -0.8306 |
| one representative per correlated cluster | growth_entropy | -0.7975 |
| one representative per correlated cluster | late_growth_fraction | -0.6122 |
| one representative per correlated cluster | log_peak_growth_km2_per_day | -0.3897 |
| one representative per correlated cluster | terminal_taper_fraction | 0.7539 |
| one representative per correlated cluster | width_p05 | 0.8311 |
| one representative per correlated cluster | front_loaded_fraction | 0.8526 |
| one representative per correlated cluster | growth_p05 | 0.8997 |
| profiles normalized independently of final size | log_duration_days | -0.9397 |
| profiles normalized independently of final size | growth_entropy | -0.9156 |
| profiles normalized independently of final size | log_final_area_km2 | -0.8090 |
| profiles normalized independently of final size | late_growth_fraction | -0.7734 |
| profiles normalized independently of final size | observation_count | -0.7150 |
| profiles normalized independently of final size | log_peak_growth_km2_per_day | -0.1989 |
| profiles normalized independently of final size | terminal_taper_fraction | 0.6045 |
| profiles normalized independently of final size | width_p05 | 0.9257 |
| profiles normalized independently of final size | front_loaded_fraction | 0.9486 |
| profiles normalized independently of final size | growth_p05 | 0.9645 |
| pulse timing taper entropy shape variables only | growth_entropy | -0.9070 |
| pulse timing taper entropy shape variables only | log_duration_days | -0.8823 |
| pulse timing taper entropy shape variables only | late_growth_fraction | -0.8440 |
| pulse timing taper entropy shape variables only | log_final_area_km2 | -0.7543 |
| pulse timing taper entropy shape variables only | observation_count | -0.6399 |
| pulse timing taper entropy shape variables only | log_peak_growth_km2_per_day | -0.1772 |
| pulse timing taper entropy shape variables only | terminal_taper_fraction | 0.5524 |
| pulse timing taper entropy shape variables only | growth_p05 | 0.9071 |
| pulse timing taper entropy shape variables only | width_p05 | 0.9201 |
| pulse timing taper entropy shape variables only | front_loaded_fraction | 0.9345 |
| scale variables removed | log_duration_days | -0.9427 |
| scale variables removed | growth_entropy | -0.9156 |
| scale variables removed | log_final_area_km2 | -0.8135 |
| scale variables removed | late_growth_fraction | -0.7770 |
| scale variables removed | observation_count | -0.7249 |
| scale variables removed | log_peak_growth_km2_per_day | -0.2029 |
| scale variables removed | terminal_taper_fraction | 0.6130 |
| scale variables removed | width_p05 | 0.9244 |
| scale variables removed | front_loaded_fraction | 0.9469 |
| scale variables removed | growth_p05 | 0.9614 |
| summary features removed retaining profiles | log_duration_days | -0.9397 |
| summary features removed retaining profiles | growth_entropy | -0.9156 |
| summary features removed retaining profiles | log_final_area_km2 | -0.8090 |
| summary features removed retaining profiles | late_growth_fraction | -0.7734 |
| summary features removed retaining profiles | observation_count | -0.7150 |
| summary features removed retaining profiles | log_peak_growth_km2_per_day | -0.1989 |
| summary features removed retaining profiles | terminal_taper_fraction | 0.6045 |
| summary features removed retaining profiles | width_p05 | 0.9257 |
| summary features removed retaining profiles | front_loaded_fraction | 0.9486 |
| summary features removed retaining profiles | growth_p05 | 0.9645 |

## Top Loadings

| feature_set | pc | rank | feature | loading |
| --- | --- | --- | --- | --- |
| full current feature set | PC1 | 1 | growth_p02 | 0.1985 |
| full current feature set | PC1 | 2 | growth_p03 | 0.1982 |
| full current feature set | PC1 | 3 | growth_p01 | 0.1976 |
| full current feature set | PC1 | 4 | growth_p04 | 0.1973 |
| full current feature set | PC1 | 5 | growth_p05 | 0.1950 |
| full current feature set | PC1 | 6 | growth_p00 | 0.1947 |
| full current feature set | PC1 | 7 | growth_p06 | 0.1945 |
| full current feature set | PC1 | 8 | growth_p07 | 0.1929 |
| full current feature set | PC2 | 1 | terminal_taper_fraction | 0.3521 |
| full current feature set | PC2 | 2 | log_peak_growth_km2_per_day | -0.3072 |
| full current feature set | PC2 | 3 | late_growth_fraction | 0.2876 |
| full current feature set | PC2 | 4 | observation_count | -0.2711 |
| full current feature set | PC2 | 5 | reactivation_count | -0.2663 |
| full current feature set | PC2 | 6 | pulse_count | -0.2663 |
| full current feature set | PC2 | 7 | log_final_area_km2 | -0.2522 |
| full current feature set | PC2 | 8 | developmental_velocity | 0.2503 |
| full current feature set | PC3 | 1 | reactivation_count | -0.4349 |
| full current feature set | PC3 | 2 | pulse_count | -0.4349 |
| full current feature set | PC3 | 3 | peak_timing | -0.2515 |
| full current feature set | PC3 | 4 | growth_p10 | -0.2293 |
| full current feature set | PC3 | 5 | terminal_taper_fraction | -0.2187 |
| full current feature set | PC3 | 6 | growth_p09 | -0.2114 |
| full current feature set | PC3 | 7 | growth_entropy | 0.1943 |
| full current feature set | PC3 | 8 | growth_p08 | -0.1896 |
| full current feature set | PC4 | 1 | log_peak_growth_km2_per_day | -0.5179 |
| full current feature set | PC4 | 2 | log_slenderness_days_per_width | 0.4357 |
| full current feature set | PC4 | 3 | reactivation_count | 0.3389 |
| full current feature set | PC4 | 4 | pulse_count | 0.3389 |
| full current feature set | PC4 | 5 | developmental_acceleration | -0.2905 |
| full current feature set | PC4 | 6 | peak_timing | -0.2778 |
| full current feature set | PC4 | 7 | log_final_area_km2 | -0.1870 |
| full current feature set | PC4 | 8 | developmental_velocity | -0.1181 |
| full current feature set | PC5 | 1 | developmental_acceleration | -0.5827 |
| full current feature set | PC5 | 2 | log_peak_growth_km2_per_day | 0.3979 |
| full current feature set | PC5 | 3 | log_slenderness_days_per_width | -0.3195 |
| full current feature set | PC5 | 4 | peak_timing | -0.2363 |
| full current feature set | PC5 | 5 | late_growth_fraction | 0.2332 |
| full current feature set | PC5 | 6 | growth_entropy | 0.1678 |
| full current feature set | PC5 | 7 | growth_p05 | -0.1545 |
| full current feature set | PC5 | 8 | width_p02 | 0.1534 |
| scale variables removed | PC1 | 1 | growth_p02 | 0.2018 |
| scale variables removed | PC1 | 2 | growth_p03 | 0.2016 |
| scale variables removed | PC1 | 3 | growth_p01 | 0.2010 |
| scale variables removed | PC1 | 4 | growth_p04 | 0.2006 |
| scale variables removed | PC1 | 5 | growth_p05 | 0.1982 |
| scale variables removed | PC1 | 6 | growth_p00 | 0.1979 |
| scale variables removed | PC1 | 7 | growth_p06 | 0.1976 |
| scale variables removed | PC1 | 8 | growth_p07 | 0.1959 |
| scale variables removed | PC2 | 1 | terminal_taper_fraction | 0.3719 |
| scale variables removed | PC2 | 2 | reactivation_count | -0.3049 |
| scale variables removed | PC2 | 3 | pulse_count | -0.3049 |
| scale variables removed | PC2 | 4 | late_growth_fraction | 0.2976 |
| scale variables removed | PC2 | 5 | observation_count | -0.2897 |
| scale variables removed | PC2 | 6 | developmental_velocity | 0.2657 |
| scale variables removed | PC2 | 7 | width_p09 | -0.2632 |
| scale variables removed | PC2 | 8 | width_p08 | -0.2469 |
| scale variables removed | PC3 | 1 | reactivation_count | 0.5213 |
| scale variables removed | PC3 | 2 | pulse_count | 0.5213 |
| scale variables removed | PC3 | 3 | terminal_taper_fraction | 0.2230 |
| scale variables removed | PC3 | 4 | observation_count | 0.2116 |
| scale variables removed | PC3 | 5 | growth_p10 | 0.2036 |
| scale variables removed | PC3 | 6 | growth_p09 | 0.1853 |
| scale variables removed | PC3 | 7 | developmental_acceleration | -0.1659 |
| scale variables removed | PC3 | 8 | growth_p08 | 0.1632 |
| scale variables removed | PC4 | 1 | developmental_acceleration | 0.5989 |
| scale variables removed | PC4 | 2 | peak_timing | 0.4157 |
| scale variables removed | PC4 | 3 | growth_entropy | -0.2484 |
| scale variables removed | PC4 | 4 | late_growth_fraction | -0.2039 |
| scale variables removed | PC4 | 5 | width_p01 | -0.1870 |
| scale variables removed | PC4 | 6 | width_p02 | -0.1852 |
| scale variables removed | PC4 | 7 | width_p00 | -0.1823 |
| scale variables removed | PC4 | 8 | growth_p06 | 0.1697 |
| scale variables removed | PC5 | 1 | developmental_velocity | -0.5591 |
| scale variables removed | PC5 | 2 | developmental_acceleration | -0.3482 |
| scale variables removed | PC5 | 3 | reactivation_count | -0.3065 |
| scale variables removed | PC5 | 4 | pulse_count | -0.3065 |
| scale variables removed | PC5 | 5 | observation_count | 0.2876 |
| scale variables removed | PC5 | 6 | late_growth_fraction | -0.2843 |
| scale variables removed | PC5 | 7 | growth_entropy | -0.2038 |
| scale variables removed | PC5 | 8 | width_p05 | -0.1871 |
| final area removed | PC1 | 1 | growth_p02 | 0.1999 |
| final area removed | PC1 | 2 | growth_p03 | 0.1997 |
| final area removed | PC1 | 3 | growth_p01 | 0.1990 |
| final area removed | PC1 | 4 | growth_p04 | 0.1987 |
| final area removed | PC1 | 5 | growth_p05 | 0.1964 |
| final area removed | PC1 | 6 | growth_p00 | 0.1960 |
| final area removed | PC1 | 7 | growth_p06 | 0.1958 |
| final area removed | PC1 | 8 | growth_p07 | 0.1941 |
| final area removed | PC2 | 1 | terminal_taper_fraction | -0.3688 |
| final area removed | PC2 | 2 | late_growth_fraction | -0.2917 |
| final area removed | PC2 | 3 | log_peak_growth_km2_per_day | 0.2867 |
| final area removed | PC2 | 4 | pulse_count | 0.2843 |
| final area removed | PC2 | 5 | reactivation_count | 0.2843 |
| final area removed | PC2 | 6 | observation_count | 0.2830 |
| final area removed | PC2 | 7 | width_p09 | 0.2555 |
| final area removed | PC2 | 8 | developmental_velocity | -0.2543 |
| final area removed | PC3 | 1 | pulse_count | 0.4878 |
| final area removed | PC3 | 2 | reactivation_count | 0.4878 |
| final area removed | PC3 | 3 | terminal_taper_fraction | 0.2156 |
| final area removed | PC3 | 4 | growth_p10 | 0.2151 |
| final area removed | PC3 | 5 | peak_timing | 0.2083 |
| final area removed | PC3 | 6 | observation_count | 0.2025 |
| final area removed | PC3 | 7 | growth_p09 | 0.1972 |
| final area removed | PC3 | 8 | growth_entropy | -0.1790 |
| final area removed | PC4 | 1 | log_peak_growth_km2_per_day | -0.5717 |
| final area removed | PC4 | 2 | log_slenderness_days_per_width | 0.4716 |
| final area removed | PC4 | 3 | peak_timing | -0.3131 |
| final area removed | PC4 | 4 | developmental_acceleration | -0.3105 |
| final area removed | PC4 | 5 | pulse_count | 0.2421 |
| final area removed | PC4 | 6 | reactivation_count | 0.2421 |
| final area removed | PC4 | 7 | growth_entropy | 0.1338 |
| final area removed | PC4 | 8 | log_duration_days | 0.1111 |
| final area removed | PC5 | 1 | developmental_acceleration | 0.5654 |
| final area removed | PC5 | 2 | log_peak_growth_km2_per_day | -0.4303 |
| final area removed | PC5 | 3 | log_slenderness_days_per_width | 0.3438 |
| final area removed | PC5 | 4 | late_growth_fraction | -0.2298 |
| final area removed | PC5 | 5 | peak_timing | 0.2270 |
| final area removed | PC5 | 6 | growth_entropy | -0.1655 |
| final area removed | PC5 | 7 | growth_p05 | 0.1538 |
| final area removed | PC5 | 8 | growth_p06 | 0.1521 |
| duration and observation count removed | PC1 | 1 | growth_p02 | 0.2040 |
| duration and observation count removed | PC1 | 2 | growth_p03 | 0.2037 |
| duration and observation count removed | PC1 | 3 | growth_p01 | 0.2031 |
| duration and observation count removed | PC1 | 4 | growth_p04 | 0.2027 |
| duration and observation count removed | PC1 | 5 | growth_p05 | 0.2003 |
| duration and observation count removed | PC1 | 6 | growth_p00 | 0.2001 |
| duration and observation count removed | PC1 | 7 | growth_p06 | 0.1996 |
| duration and observation count removed | PC1 | 8 | growth_entropy | -0.1980 |
| duration and observation count removed | PC2 | 1 | terminal_taper_fraction | 0.3883 |
| duration and observation count removed | PC2 | 2 | log_peak_growth_km2_per_day | -0.3405 |
| duration and observation count removed | PC2 | 3 | late_growth_fraction | 0.2861 |
| duration and observation count removed | PC2 | 4 | log_final_area_km2 | -0.2715 |
| duration and observation count removed | PC2 | 5 | width_p09 | -0.2521 |
| duration and observation count removed | PC2 | 6 | pulse_count | -0.2468 |
| duration and observation count removed | PC2 | 7 | reactivation_count | -0.2468 |
| duration and observation count removed | PC2 | 8 | width_p08 | -0.2376 |
| duration and observation count removed | PC3 | 1 | pulse_count | -0.3792 |
| duration and observation count removed | PC3 | 2 | reactivation_count | -0.3792 |
| duration and observation count removed | PC3 | 3 | peak_timing | -0.3039 |
| duration and observation count removed | PC3 | 4 | log_peak_growth_km2_per_day | -0.2963 |
| duration and observation count removed | PC3 | 5 | log_slenderness_days_per_width | 0.2790 |
| duration and observation count removed | PC3 | 6 | growth_p10 | -0.2243 |
| duration and observation count removed | PC3 | 7 | growth_entropy | 0.2191 |
| duration and observation count removed | PC3 | 8 | growth_p09 | -0.2098 |
| duration and observation count removed | PC4 | 1 | pulse_count | -0.4764 |
| duration and observation count removed | PC4 | 2 | reactivation_count | -0.4764 |
| duration and observation count removed | PC4 | 3 | log_peak_growth_km2_per_day | 0.4315 |
| duration and observation count removed | PC4 | 4 | log_slenderness_days_per_width | -0.3725 |
| duration and observation count removed | PC4 | 5 | developmental_acceleration | 0.2842 |
| duration and observation count removed | PC4 | 6 | peak_timing | 0.2281 |
| duration and observation count removed | PC4 | 7 | developmental_velocity | 0.1544 |
| duration and observation count removed | PC4 | 8 | log_final_area_km2 | 0.1366 |
| duration and observation count removed | PC5 | 1 | developmental_acceleration | -0.5889 |
| duration and observation count removed | PC5 | 2 | log_peak_growth_km2_per_day | 0.4048 |
| duration and observation count removed | PC5 | 3 | log_slenderness_days_per_width | -0.3270 |
| duration and observation count removed | PC5 | 4 | late_growth_fraction | 0.2340 |
| duration and observation count removed | PC5 | 5 | peak_timing | -0.2278 |
| duration and observation count removed | PC5 | 6 | growth_entropy | 0.1607 |
| duration and observation count removed | PC5 | 7 | width_p02 | 0.1536 |
| duration and observation count removed | PC5 | 8 | width_p01 | 0.1534 |
| all scale and duration variables removed | PC1 | 1 | growth_p02 | 0.2075 |
| all scale and duration variables removed | PC1 | 2 | growth_p03 | 0.2072 |
| all scale and duration variables removed | PC1 | 3 | growth_p01 | 0.2066 |
| all scale and duration variables removed | PC1 | 4 | growth_p04 | 0.2061 |
| all scale and duration variables removed | PC1 | 5 | growth_p05 | 0.2036 |
| all scale and duration variables removed | PC1 | 6 | growth_p00 | 0.2035 |
| all scale and duration variables removed | PC1 | 7 | growth_p06 | 0.2028 |
| all scale and duration variables removed | PC1 | 8 | growth_entropy | -0.2018 |
| all scale and duration variables removed | PC2 | 1 | terminal_taper_fraction | 0.4198 |
| all scale and duration variables removed | PC2 | 2 | late_growth_fraction | 0.2961 |
| all scale and duration variables removed | PC2 | 3 | reactivation_count | -0.2786 |
| all scale and duration variables removed | PC2 | 4 | pulse_count | -0.2786 |
| all scale and duration variables removed | PC2 | 5 | width_p09 | -0.2704 |
| all scale and duration variables removed | PC2 | 6 | width_p08 | -0.2563 |
| all scale and duration variables removed | PC2 | 7 | developmental_velocity | 0.2466 |
| all scale and duration variables removed | PC2 | 8 | growth_p10 | 0.2302 |
| all scale and duration variables removed | PC3 | 1 | reactivation_count | 0.5915 |
| all scale and duration variables removed | PC3 | 2 | pulse_count | 0.5915 |
| all scale and duration variables removed | PC3 | 3 | developmental_velocity | -0.1742 |
| all scale and duration variables removed | PC3 | 4 | growth_p10 | 0.1675 |
| all scale and duration variables removed | PC3 | 5 | terminal_taper_fraction | 0.1659 |
| all scale and duration variables removed | PC3 | 6 | growth_entropy | -0.1545 |
| all scale and duration variables removed | PC3 | 7 | growth_p09 | 0.1526 |
| all scale and duration variables removed | PC3 | 8 | developmental_acceleration | -0.1424 |
| all scale and duration variables removed | PC4 | 1 | developmental_acceleration | -0.5989 |
| all scale and duration variables removed | PC4 | 2 | peak_timing | -0.4176 |
| all scale and duration variables removed | PC4 | 3 | growth_entropy | 0.2527 |
| all scale and duration variables removed | PC4 | 4 | late_growth_fraction | 0.2062 |
| all scale and duration variables removed | PC4 | 5 | width_p01 | 0.1865 |
| all scale and duration variables removed | PC4 | 6 | width_p02 | 0.1850 |
| all scale and duration variables removed | PC4 | 7 | width_p00 | 0.1819 |
| all scale and duration variables removed | PC4 | 8 | growth_p06 | -0.1724 |
| all scale and duration variables removed | PC5 | 1 | developmental_velocity | 0.6597 |
| all scale and duration variables removed | PC5 | 2 | late_growth_fraction | 0.3612 |
| all scale and duration variables removed | PC5 | 3 | growth_entropy | 0.2032 |
| all scale and duration variables removed | PC5 | 4 | width_p07 | 0.1957 |
| all scale and duration variables removed | PC5 | 5 | reactivation_count | 0.1932 |
| all scale and duration variables removed | PC5 | 6 | pulse_count | 0.1932 |
| all scale and duration variables removed | PC5 | 7 | width_p08 | 0.1915 |
| all scale and duration variables removed | PC5 | 8 | width_p06 | 0.1893 |
| normalized profile variables only | PC1 | 1 | growth_p02 | 0.2312 |
| normalized profile variables only | PC1 | 2 | growth_p03 | 0.2311 |
| normalized profile variables only | PC1 | 3 | growth_p04 | 0.2301 |
| normalized profile variables only | PC1 | 4 | growth_p01 | 0.2301 |
| normalized profile variables only | PC1 | 5 | growth_p05 | 0.2276 |
| normalized profile variables only | PC1 | 6 | growth_p06 | 0.2268 |
| normalized profile variables only | PC1 | 7 | growth_p00 | 0.2264 |
| normalized profile variables only | PC1 | 8 | growth_p07 | 0.2249 |
| normalized profile variables only | PC2 | 1 | width_p09 | -0.3694 |
| normalized profile variables only | PC2 | 2 | width_p08 | -0.3657 |
| normalized profile variables only | PC2 | 3 | width_p07 | -0.3453 |
| normalized profile variables only | PC2 | 4 | growth_p10 | 0.3418 |
| normalized profile variables only | PC2 | 5 | growth_p09 | 0.3093 |
| normalized profile variables only | PC2 | 6 | width_p06 | -0.3053 |
| normalized profile variables only | PC2 | 7 | growth_p08 | 0.2707 |
| normalized profile variables only | PC2 | 8 | width_p05 | -0.2576 |
| normalized profile variables only | PC3 | 1 | width_p02 | 0.3418 |
| normalized profile variables only | PC3 | 2 | width_p01 | 0.3409 |
| normalized profile variables only | PC3 | 3 | width_p00 | 0.3307 |
| normalized profile variables only | PC3 | 4 | width_p09 | -0.3287 |
| normalized profile variables only | PC3 | 5 | width_p03 | 0.3066 |
| normalized profile variables only | PC3 | 6 | width_p08 | -0.2937 |
| normalized profile variables only | PC3 | 7 | growth_p06 | -0.2333 |
| normalized profile variables only | PC3 | 8 | width_p04 | 0.2204 |
| normalized profile variables only | PC4 | 1 | width_p05 | -0.4249 |
| normalized profile variables only | PC4 | 2 | width_p09 | 0.3833 |
| normalized profile variables only | PC4 | 3 | width_p00 | 0.3139 |
| normalized profile variables only | PC4 | 4 | width_p04 | -0.3077 |
| normalized profile variables only | PC4 | 5 | width_p08 | 0.2831 |
| normalized profile variables only | PC4 | 6 | growth_p00 | 0.2769 |
| normalized profile variables only | PC4 | 7 | width_p06 | -0.2698 |
| normalized profile variables only | PC4 | 8 | width_p01 | 0.2338 |
| normalized profile variables only | PC5 | 1 | width_p00 | -0.3671 |
| normalized profile variables only | PC5 | 2 | width_p03 | 0.3305 |
| normalized profile variables only | PC5 | 3 | width_p09 | 0.3298 |
| normalized profile variables only | PC5 | 4 | width_p06 | -0.3147 |
| normalized profile variables only | PC5 | 5 | growth_p05 | -0.2986 |
| normalized profile variables only | PC5 | 6 | growth_p06 | -0.2634 |
| normalized profile variables only | PC5 | 7 | width_p07 | -0.2517 |
| normalized profile variables only | PC5 | 8 | width_p04 | 0.2513 |
| growth-share profile only | PC1 | 1 | growth_p06 | 0.3044 |
| growth-share profile only | PC1 | 2 | growth_p04 | 0.3043 |
| growth-share profile only | PC1 | 3 | growth_p07 | 0.3039 |
| growth-share profile only | PC1 | 4 | growth_p03 | 0.3036 |
| growth-share profile only | PC1 | 5 | growth_p05 | 0.3030 |
| growth-share profile only | PC1 | 6 | growth_p08 | 0.3030 |
| growth-share profile only | PC1 | 7 | growth_p02 | 0.3024 |
| growth-share profile only | PC1 | 8 | growth_p09 | 0.3009 |
| growth-share profile only | PC2 | 1 | growth_p00 | 0.4456 |
| growth-share profile only | PC2 | 2 | growth_p10 | -0.4079 |
| growth-share profile only | PC2 | 3 | growth_p01 | 0.3907 |
| growth-share profile only | PC2 | 4 | growth_p09 | -0.3624 |
| growth-share profile only | PC2 | 5 | growth_p02 | 0.3258 |
| growth-share profile only | PC2 | 6 | growth_p08 | -0.3107 |
| growth-share profile only | PC2 | 7 | growth_p07 | -0.2442 |
| growth-share profile only | PC2 | 8 | growth_p03 | 0.2341 |
| growth-share profile only | PC3 | 1 | growth_p05 | 0.4977 |
| growth-share profile only | PC3 | 2 | growth_p00 | -0.4145 |
| growth-share profile only | PC3 | 3 | growth_p10 | -0.3996 |
| growth-share profile only | PC3 | 4 | growth_p04 | 0.3784 |

## Sample Size And Exclusion Rules

- Full feature-set analyses use all rows in `developmental_morphospace_features.parquet`.
- Duration sensitivity repeats the full PCA for fires lasting at least 2, 4, 8, and 10 days.
- The correlated-cluster ablation greedily keeps one feature per absolute-correlation cluster using threshold 0.85 on a fixed 25,000-fire sample.
- Log columns are computed with lower clipping at 1e-9.
