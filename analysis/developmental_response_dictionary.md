# Developmental Response Dictionary

This revision separates absolute-scale outcomes from shape-normalized developmental responses. Climate can be associated with final size, timing, or shape; those are not interchangeable.

| Response | Field or formula | Interpretation | Sensitivity | One-day fires | Use |
|---|---|---|---|---|---|
| Final area | `final_area_km2` | Total mapped burned area for the event. | absolute scale outcome; not shape-normalized | yes | final outcome |
| Duration | `duration_days` | Number of days spanned by the observed fire history. | strongly duration-sensitive | yes | final outcome |
| Peak growth | `peak_growth_km2_per_day` | Largest daily area increment. | scale-sensitive | available if at least one slice | final outcome |
| Peak timing | `peak_timing` | Relative position of largest growth day in the observed sequence. | duration-sensitive for short fires | degenerate for one-day fires | shape timing |
| Front-loaded fraction | `front_loaded_fraction` | Fraction of growth allocated to early development. | moderately duration-sensitive | available but coarse for one-day fires | shape-normalized |
| Late-growth fraction | `late_growth_fraction` | Fraction of growth allocated to late development. | moderately duration-sensitive | available but coarse for one-day fires | shape-normalized |
| Terminal taper | `terminal_taper_fraction` | Degree to which growth decelerates near termination. | duration-sensitive | degenerate for one-day fires | shape-normalized |
| Growth entropy | `growth_entropy` | Evenness of daily growth allocation through time. | sensitive to number of observed slices | low information for one-day fires | shape-normalized |
| Pulse count | `pulse_count` | Number of major growth pulses detected from daily increments. | increases with duration/opportunity | available but minimally informative for one-day fires | absolute/shape hybrid |
| Reactivation count | `reactivation_count` | Number of renewed growth periods after quiescence. | requires multi-day histories | not meaningful for one-day fires | shape process |
| Developmental velocity | `developmental_velocity` | Mean normalized growth progression through developmental time. | less scale-sensitive, duration-sensitive | available | shape-normalized |
| Developmental acceleration | `developmental_acceleration` | Change in growth rate through the observed sequence. | sensitive to short sequences | degenerate for one-day fires | shape-normalized |
| VASE widths | `width_p00` to `width_p10` | Interpolated ring widths over normalized developmental time. | shape-normalized if using normalized width | available | shape representation |
| Major VASE axes | `morph_pc1` to `morph_pc5` | Principal components of standardized developmental features. | can mix scale and shape unless adjusted | available | compact representation |
| Current growth state | `current_growth_log1p`, `current_cumulative_log1p`, `elapsed_day` | State variables available up to day t for next-day growth models. | absolute-scale partial history | not applicable | time-varying state |

State-dependent models in this revision avoid final-duration and final-area leakage by using elapsed day, current daily growth, current cumulative area, and recent acceleration rather than normalized developmental time or final cumulative fraction.
