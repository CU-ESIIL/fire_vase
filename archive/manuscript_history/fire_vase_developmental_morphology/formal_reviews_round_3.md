# Formal Reviews Round 3

Date: 2026-07-22

Object reviewed: `output/pdf/fire_vase_developmental_morphology_manuscript.pdf`
after integrating the PC1 robustness and null-developmental-universe analyses.

## Review 1: Fire Science And Inference

The revision is substantially more credible than the previous draft. The
central claim now matches the evidence: Fire VASE provides a reproducible
coordinate system for observed fire histories. The abstract appropriately
states that low dimensionality is partly shaped by cumulative-profile
redundancy and short fires, and the climate section no longer implies a
mechanistic attribution. This is the right direction.

The remaining weakness was rhetorical rather than analytical. Several phrases
still sounded as if the manuscript were reporting its own revision history
instead of presenting a polished result. In particular, "the revised claim" and
"the audit analyses replace" should disappear from the paper. Readers should
see the current argument, not the workshop trail.

Recommended edits:
- Present Figure 3 as an analysis result, not as an audit artifact.
- Replace "shape" with "form" in places where "shape" sounds too categorical.
- Keep perimeter/active-edge climate exposure as a clear next step, but do not
  let the caveat overwhelm the climate proof of concept.

## Review 2: Quantitative Morphometrics And Null Models

The new Figure 3 is the strongest improvement from the last round. It shows
that PC1 is stable across several feature definitions while also showing that
profile encodings can be low dimensional by construction. This is exactly the
balance needed for a defensible morphospace paper.

The figure is readable after the label cleanup, but the manuscript should be
even more explicit that low dimensionality is a property of the observed
representation, not proof of a small physically reachable set. The text already
says this, but the Figure 1 legend phrase "collapse into" still sounded more
deterministic than necessary.

Recommended edits:
- Replace "collapse into" with "can be organized in" for Figure 1.
- Keep the null hierarchy in the main figure sequence.
- Retain the fixed-day prediction analysis as supplementary only.

## Review 3: Presentation, Figure Flow, And Science Format

The four-figure structure is much easier to read than the five-figure version.
The manuscript now has a clearer shape: representation, atlas, robustness/nulls,
and climate projection. That sequence works.

The PDF layout still had one visible flaw: the one-sentence summary was pushed
onto an almost empty second page. That made the manuscript feel less polished
than the science. The climate panel also still used "Predictive coupling" and
"Held-out prediction accuracy," which are broader and less human-readable than
the current interpretation.

Recommended edits:
- Shorten the abstract enough that the one-sentence summary stays with the
  title page.
- Rename Figure 4C as a climate-shape association panel.
- Use "Held-out variance explained (R2)" rather than "prediction accuracy."
- Make capitalization in Results and Methods headings consistent.

## Editorial Response

Implemented in this round:
- Shortened and tightened the abstract while preserving the key numbers.
- Changed "The revised claim is conservative" to "The claim is intentionally
  conservative."
- Removed internal process language from the Figure 3 Results section.
- Replaced "collapse into" with "can be organized in" in the Figure 1 legend
  and manuscript caption.
- Changed Figure 4C to "Climate-shape association" with the x-axis label
  "Held-out variance explained (R2)."
- Reworded climate association language as shape recovered from climate and
  climate recovered from shape.
- Made section-heading capitalization more consistent.

Remaining pre-submission needs:
- Add final author list, affiliations, funding, contribution statements, and
  data-availability links.
- Replace centroid climate exposure with perimeter, active-area, edge, and
  local-anomaly climate analyses before making mechanistic climate claims.
- Run the heavier final validation setting, such as 500 bootstrap/null
  replicates, before submission-ready numbers are frozen.
