#!/usr/bin/env python3
"""Create a science-paper-style PDF draft for the Fire VASE manuscript."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/pdf/fire_vase_developmental_morphology_manuscript.pdf"
MANIFEST = ROOT / "output/pdf/fire_vase_developmental_morphology_manuscript_manifest.json"
COMPLIANCE_NOTE = ROOT / "docs/manuscripts/fire_vase_developmental_morphology/science_author_guidelines_compliance.md"
FIGURE_DIR = ROOT / "tmp/pdfs/fire_vase_manuscript_figures"
MAIN_FIGURE_DIR = ROOT / "figures/main"
SUPPLEMENT_DIR = ROOT / "figures/supplement"

PAGE_W, PAGE_H = letter
MARGIN_X = 1.0 * inch
MARGIN_Y = 1.0 * inch
TEXT_H = PAGE_H - 2 * MARGIN_Y
INK = colors.HexColor("#171717")
MUTED = colors.HexColor("#5d6268")
RULE = colors.HexColor("#d9d9d9")


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PaperTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=INK,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=20,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "abstract_head": ParagraphStyle(
            "AbstractHead",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=24,
            textColor=INK,
            alignment=TA_LEFT,
            spaceBefore=6,
            spaceAfter=0,
        ),
        "abstract": ParagraphStyle(
            "Abstract",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=12,
            leading=24,
            alignment=TA_LEFT,
            textColor=INK,
            spaceAfter=6,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=24,
            textColor=INK,
            spaceBefore=8,
            spaceAfter=0,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=24,
            textColor=INK,
            spaceBefore=6,
            spaceAfter=0,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=12,
            leading=24,
            alignment=TA_LEFT,
            textColor=INK,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Times-Roman",
            fontSize=10,
            leading=18,
            alignment=TA_LEFT,
            textColor=INK,
            spaceAfter=5,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.7,
            leading=11.6,
            alignment=TA_LEFT,
            textColor=INK,
            spaceBefore=6,
            spaceAfter=8,
        ),
    }


def draw_line_numbers(canvas, _doc) -> None:
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(MUTED)
    y = PAGE_H - MARGIN_Y - 5
    line = 1
    while y > MARGIN_Y:
        if line % 5 == 0:
            canvas.drawRightString(MARGIN_X - 0.22 * inch, y, str(line))
        y -= 24
        line += 1


def page_header(canvas, doc) -> None:
    canvas.saveState()
    canvas.setTitle("Fire VASE Provides a Low-Dimensional Coordinate System for Wildfire Development")
    canvas.setAuthor("CubeDynamics Fire VASE manuscript draft")
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.35)
    canvas.line(MARGIN_X, PAGE_H - 0.55 * inch, PAGE_W - MARGIN_X, PAGE_H - 0.55 * inch)
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN_X, PAGE_H - 0.43 * inch, "Fire VASE developmental morphology - Science initial-submission style")
    canvas.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 0.43 * inch, str(doc.page))
    draw_line_numbers(canvas, doc)
    canvas.restoreState()


def make_doc(path: Path) -> BaseDocTemplate:
    full = Frame(
        MARGIN_X,
        MARGIN_Y,
        PAGE_W - 2 * MARGIN_X,
        TEXT_H,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    return BaseDocTemplate(
        str(path),
        pagesize=letter,
        pageTemplates=[
            PageTemplate(id="First", frames=[full], onPage=page_header),
            PageTemplate(id="Text", frames=[full], onPage=page_header),
            PageTemplate(id="Figure", frames=[full], onPage=page_header),
        ],
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_Y,
        bottomMargin=MARGIN_Y,
    )


def p(text: str, style: ParagraphStyle) -> Paragraph:
    text = text.replace("R2", "R<super>2</super>").replace("km2", "km<super>2</super>")
    return Paragraph(text, style)


def add_section(story, title: str, paragraphs: list[str], st: dict[str, ParagraphStyle]) -> None:
    story.append(p(title, st["h1"]))
    for para in paragraphs:
        story.append(p(para, st["body"]))


def add_subsection(story, title: str, paragraphs: list[str], st: dict[str, ParagraphStyle]) -> None:
    story.append(p(title, st["h2"]))
    for para in paragraphs:
        story.append(p(para, st["body"]))


def figure_flowable(number: int, image_path: Path, caption: str, st: dict[str, ParagraphStyle]) -> KeepTogether:
    usable_w = PAGE_W - 2 * MARGIN_X
    with PILImage.open(image_path) as im:
        w_px, h_px = im.size
    img_w = usable_w
    img_h = img_w * h_px / w_px
    max_h = 5.35 * inch
    if img_h > max_h:
        img_h = max_h
        img_w = img_h * w_px / h_px
    image = Image(str(image_path), width=img_w, height=img_h)
    image.hAlign = "CENTER"
    cap = p(f"<b>Figure {number}.</b> {caption}", st["caption"])
    return KeepTogether([image, cap])


def prepare_figure_images() -> dict[str, Path]:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    source_images = {
        "figure_1": MAIN_FIGURE_DIR / "Figure_1.png",
        "figure_2": MAIN_FIGURE_DIR / "Figure_2.png",
        "figure_3": MAIN_FIGURE_DIR / "Figure_3.png",
        "figure_4": MAIN_FIGURE_DIR / "Figure_4.png",
    }
    out: dict[str, Path] = {}
    for name, source in source_images.items():
        if not source.exists():
            raise FileNotFoundError(f"Missing main figure image: {source}")
        target = FIGURE_DIR / f"{name}.png"
        with PILImage.open(source) as im:
            im.convert("RGB").save(target)
        out[name] = target
    return out


def build_story() -> list:
    st = styles()
    story: list = []
    story.append(p("Fire VASE Provides a Low-Dimensional Coordinate System for Wildfire Development", st["title"]))
    story.append(p("Article type: Research Article | Initial-submission style draft | 22 July 2026", st["subtitle"]))
    story.append(p("Authors", st["abstract_head"]))
    story.append(p("Tuff et al.; author affiliations, corresponding author email, and ORCID identifiers to be finalized before submission.", st["abstract"]))
    story.append(p("Abstract", st["abstract_head"]))
    story.append(
        p(
            "Wildfire events are usually compared by final area, perimeter, duration, or daily growth, even though impact and management opportunity depend on how a fire develops through time. We introduce Fire VASE, a geometry-first representation that converts each observed fire history into a comparable developmental object. Applied to 278,569 FIRED events from 2000-2021, Fire VASE defines a reproducible low-dimensional coordinate system: five geometry-only axes explain 96.3% of standardized feature variance, with PC1 explaining 81.0%. Real-fire medoids reveal recurring neighborhoods arranged along continuous gradients rather than hard classes. Null and sensitivity analyses show that low dimensionality is robust but partly shaped by cumulative-profile redundancy and short fires, so we do not claim that observed fires occupy a restricted subset of all plausible trajectories. Projecting gridMET climate onto 237,235 climate-complete fires shows alignment with temperature, vapor pressure deficit, and wind, but blocked validation and matched examples show that climate and morphology are not interchangeable. Fire VASE is therefore a coordinate system for organizing observed fire development before richer perimeter-based climate, fuel, topographic, and management explanations are added.",
            st["abstract"],
        )
    )
    story.append(p("One Sentence Summary", st["abstract_head"]))
    story.append(p("Fire VASE turns real wildfire histories into a shared low-dimensional coordinate system for comparing developmental form.", st["abstract"]))
    story.append(NextPageTemplate("Text"))
    story.append(PageBreak())

    add_section(
        story,
        "Introduction",
        [
            "Wildfire science now measures fire at continental scales. Satellite burned-area products map burned pixels, event-building algorithms reconstruct fire histories, and gridded meteorological products describe the atmospheric context in which those events unfold [1-4]. Those tools have helped show that fire spread and area burned depend on weather, vapor pressure deficit, fuels, topography, antecedent aridity, ignition context, and human activity [5-11].",
            "Yet the common units of comparison remain incomplete for developmental questions. A final perimeter or final area describes the outcome, and daily growth describes a sequence, but neither gives every fire a compact position in a shared space of whole-history form. That matters because two fires with similar final area can arrive there through very different histories: a single explosive pulse, a persistent narrow burn, a front-loaded plateau, or a late reactivation.",
            "Fire VASE addresses this representational gap by borrowing the logic of morphospace and geometric morphometrics: complex forms become comparable when they are embedded in a shared coordinate system [12-14]. For each fire event, cumulative burned area is mapped to radial width and event time is mapped to vertical position, producing a vase-like object whose rings preserve the order of observed growth. The representation is deliberately geometry-first: climate and other covariates are added only after the developmental coordinate system is defined. This separation lets us ask what structure is present in fire history itself before asking which environmental variables explain that structure.",
            "The claim is intentionally conservative. We do not argue that wildfires are confined to a small subset of every mathematically possible growth history. Instead, we ask whether observed events can be embedded in a reproducible low-dimensional coordinate system, whether that system contains recurring real-fire landmarks, and whether climate can be projected onto it without being treated as the sole cause of form.",
        ],
        st,
    )

    story.append(p("Results", st["h1"]))

    add_subsection(
        story,
        "A geometry-first representation makes whole fires comparable",
        [
            "The analysis includes 278,569 real FIRED events and 626,102 daily VASE slices from 2000-2021. Each VASE is generated directly from observed event histories rather than from simulated or synthetic fires. Developmental time is plotted from bottom to top, and cumulative burned area is encoded as ring width. The resulting glyph keeps daily ordering visible while making histories comparable across the full population (Fig. 1A).",
            "The observed population is strongly skewed toward short and small events. The median fire lasts 1 day, the 75th percentile lasts 4 days, the 90th percentile lasts 8 days, and the longest event in the table lasts 85 days. Final area is also skewed: the median event reaches 0.43 km2, the 99th percentile reaches 27.48 km2, and the maximum reaches 3503.87 km2. These properties are part of the object of analysis rather than filtering artifacts, but they are important when interpreting low-dimensional structure.",
        ],
        st,
    )

    add_subsection(
        story,
        "Observed fire histories define a reproducible low-dimensional coordinate system",
        [
            "Geometry-only principal component analysis places all events in a shared morphospace (Fig. 1B). Across the full population, five axes explain 96.3% of standardized VASE-feature variance. PC1 explains 81.0%, followed by PC2 at 6.6%, PC3 at 3.5%, PC4 at 3.3%, and PC5 at 1.8% (Fig. 1C). Stratified bootstrap resampling confirms that this coordinate system is stable for the observed population, with PC1-PC5 cumulative variance concentrated around the same value and high five-dimensional subspace overlap.",
            "Null and sensitivity analyses qualify the interpretation. A feature-wise permutation null, which destroys covariance among geometry features, reduces first-five-axis variance to about 42.6%. A within-fire growth-timing permutation remains much closer to the observed value at about 95.7%, showing that the monotone and redundant structure of cumulative growth histories contributes substantially to the result. Excluding short fires also weakens low dimensionality; among fires lasting at least 10 days, the first five axes explain 78.5%. The robust claim is therefore that Fire VASE provides a reproducible coordinate system for observed histories, not that all plausible trajectories are sharply excluded.",
        ],
        st,
    )

    add_subsection(
        story,
        "An atlas of real fires reveals recurring neighborhoods rather than hard classes",
        [
            "Representative VASEs were selected as real medoid fires in PC1-PC3 space. The main atlas displays the 18 highest-occupancy medoids over the population density field (Fig. 2A). These landmarks are observed fires, not idealized templates. They make the occupied space readable while preserving the continuous nature of the coordinates.",
            "Coverage improves as additional medoids are added (Fig. 2B-C), showing that a compact atlas can summarize much of the occupied space while still retaining variation. Transects through the first three axes show gradual changes in real fire form rather than abrupt boundaries (Fig. 2D). Shape labels such as single flash, skinny persistent, compact steady, multi-pulse complex, front-loaded plateau, and late surge are therefore best treated as field-guide terms for neighborhoods. Local-neighborhood purity exceeds a class-frequency reference, but overlap remains substantial (Fig. 2E).",
        ],
        st,
    )

    add_subsection(
        story,
        "The dominant axis is robust but partly redundant",
        [
            "Feature ablations and null comparisons test how much of the dominant structure survives feature choices and alternative developmental histories (Fig. 3). PC1 remains large after scale and duration variables are removed, and the first five axes remain high-variance under several feature subsets. This indicates that the coordinate system is not simply a final-size or duration ranking.",
            "These analyses also show why stronger constraint language should be avoided. Profile-only and growth-share-only feature sets are extremely low dimensional because their encodings are themselves redundant. Null developmental universes that preserve duration, final area, zero-growth frequency, empirical increments, or duration-bin mean profiles often approach the observed first-five-axis variance. Support-overlap diagnostics further show that the null populations are not cleanly separated from observed fires in PC1-PC5 space. PC1 is therefore best interpreted as a reproducible developmental-profile axis whose biological interpretation requires stricter future nulls and richer covariates.",
        ],
        st,
    )

    add_subsection(
        story,
        "Climate aligns with morphology but does not define it",
        [
            "Daily gridMET climate attribution is available for 237,235 climate-complete fires. The current extraction is daily and centroid-based, with maximum temperature, minimum temperature, vapor pressure deficit (VPD), and wind speed summarized for each event. Because climate is projected onto geometry-only coordinates, the climate surfaces show association without allowing meteorology to define the morphospace (Fig. 4A-B).",
            "Held-out linear association models show that climate can recover part of morphology, especially PC1, but performance is lower and less stable under region-blocked validation than under random splits (Fig. 4C). The reverse direction is weaker: morphology recovers little of average centroid climate under conservative blocking. Matched examples and population matching make the non-equivalence visible, with some fires sharing form under contrasting climate and others sharing climate under contrasting form (Fig. 4D-E).",
            "These climate results are retained as proof of concept rather than a completed mechanistic explanation. The next manuscript-scale analysis should replace or supplement centroids with within-perimeter, newly burned area, active-edge, and perimeter-extension exposure; add climate anomalies relative to local normals; and include humidity, precipitation, fuel moisture, topography, vegetation, suppression, ignition cause, and directional wind structure.",
        ],
        st,
    )

    add_section(
        story,
        "Discussion",
        [
            "Fire VASE reframes wildfire histories as comparable developmental forms. The central contribution is not a new fire-behavior model and not a causal estimate of climate effects. It is a coordinate system: a way to place hundreds of thousands of observed fires into a common geometry-first space where recurrence, variation, analogs, and environmental projections can be studied.",
            "The results are strongest when the claim is narrow. Five geometry-only axes summarize the observed population well, and this structure is stable under resampling. Real medoids organize the space into recognizable neighborhoods, while transects and overlap analyses show that these neighborhoods are continuous rather than categorical. Climate surfaces then demonstrate that external covariates can be layered onto the same coordinates without replacing developmental form.",
            "At the same time, the robustness tests prevent overinterpretation. Low dimensionality is partly shaped by cumulative-profile redundancy and the abundance of short fires. Strict nulls that preserve duration and empirical growth structure are much closer to the observed result than simple feature permutations. Thus, Fire VASE currently supports a reproducible developmental coordinate system, not a completed theory of trajectory constraint.",
            "This conservative framing still opens productive tests. Fires near one another in VASE space can be compared for shared climate exposure, fuel condition, terrain, ignition context, or management history. Fires that are climate-similar but morphologically different may identify missing controls. Fires that are morphologically similar under contrasting climates may reveal compensating pathways. These are the comparisons a developmental coordinate system makes possible.",
            "Several caveats define the next stage. Climate attribution is still daily and centroid-based rather than perimeter- or active-edge-based. The analysis does not yet include humidity, precipitation, fuel moisture, topography, vegetation, suppression, ignition cause, or local climate anomalies. Coupling values are linear recoverability baselines rather than causal estimates. A fixed-day prediction benchmark has been moved to the supplement because blocked validation is weak and older fractional-stage predictors risked leakage. These limits sharpen the claim: Fire VASE is an instrument for organizing observed fire development before richer mechanistic explanations are added.",
        ],
        st,
    )

    story.append(p("Materials and Methods", st["h1"]))

    add_subsection(
        story,
        "Event records",
        [
            "Fire events and daily progression were derived from MODIS burned-area and FIRED-style event products in the CubeDynamics Fire VASE workflow [1-3]. The analysis table contains 278,569 events and 626,102 daily VASE slices from 2000-2021. Each event is represented as an ordered daily sequence with event identifier, date, cumulative area, daily growth, duration, and centroid coordinates where available.",
            "Climate-complete status was evaluated after gridMET extraction. A fire is climate complete when all required daily centroid samples are present for the variables used here. This yields 237,235 climate-complete fires. Fires with missing centroid climate remain in the geometry-only morphospace but are excluded from climate-coupled analyses.",
        ],
        st,
    )

    add_subsection(
        story,
        "VASE construction and geometry features",
        [
            "For each fire, developmental time is mapped to vertical position and cumulative burned area is mapped to radial width. The object is rendered as stacked rings, so each ring corresponds to one observed daily slice. Broad rings indicate larger cumulative burned area, abrupt changes in ring width indicate rapid growth, and thin or tapered regions indicate persistence or termination.",
            "Geometry-only features summarize scale, time, pulse structure, taper, entropy, and profile shape. Features include final area, duration, peak daily growth, observation count, pulse count, reactivation count, peak timing, front-loaded growth fraction, late growth fraction, terminal taper, growth entropy, developmental velocity, developmental acceleration, slenderness, and interpolated cumulative-width and daily-growth profiles. Features were standardized before principal component analysis [15].",
        ],
        st,
    )

    add_subsection(
        story,
        "Medoids, labels, and validation",
        [
            "Representative VASEs were selected as real medoid fires using farthest-point coverage in PC1-PC3, following the logic of k-center coverage algorithms [16]. Rule-based shape labels were assigned from geometry features to provide an exploratory vocabulary. These labels are used for communication and neighborhood summaries; the quantitative analyses treat morphospace as continuous.",
            "PCA stability was assessed with stratified bootstrap resampling by duration, area, year, and region [17]. Null analyses compared the observed PCA with independent feature permutation, within-fire growth-order shuffling, duration and final-area matched Dirichlet histories, zero-preserving Dirichlet histories, empirical-increment histories, and duration-bin mean-profile histories. Sensitivity analyses repeated PCA after duration filtering and feature ablation.",
        ],
        st,
    )

    add_subsection(
        story,
        "Climate and supplementary prediction",
        [
            "Daily gridMET variables were extracted at the event centroid for each VASE slice [4]. Variables include maximum temperature in degrees C, minimum temperature in degrees C, vapor pressure deficit in kPa, and wind speed in m/s. Wind is represented in the simplest current form as presence and average speed; richer directional, gust, and active-edge structure is deferred.",
            "Directional climate-morphology association was evaluated with held-out linear baseline models under random, region-blocked, and year-blocked folds. The models are written informally as climate predicting morphology and morphology predicting climate, but they are not causal estimates. Partial-history prediction is retained as Supplementary Figure 2 using only fixed observed-day predictors available by that day.",
        ],
        st,
    )

    story.append(NextPageTemplate("Text"))
    story.append(PageBreak())
    story.append(p("References and Notes", st["h1"]))
    refs = [
        "Giglio, L., Boschetti, L., Roy, D. P., Humber, M. L. and Justice, C. O. The Collection 6 MODIS burned area mapping algorithm and product. Remote Sensing of Environment 217, 72-85 (2018). doi:10.1016/j.rse.2018.08.005.",
        "Balch, J. K. et al. FIRED (Fire Events Delineation): An open, flexible algorithm and database of US fire events derived from the MODIS burned area product (2001-2019). Remote Sensing 12, 3498 (2020). doi:10.3390/rs12213498.",
        "Mahood, A. L., Lindrooth, E. J., Cook, M. C. and Balch, J. K. Country-level fire perimeter datasets (2001-2021). Scientific Data 9, 458 (2022). doi:10.1038/s41597-022-01572-3.",
        "Abatzoglou, J. T. Development of gridded surface meteorological data for ecological applications and modelling. International Journal of Climatology 33, 121-131 (2013). doi:10.1002/joc.3413.",
        "Abatzoglou, J. T. and Williams, A. P. Impact of anthropogenic climate change on wildfire across western US forests. Proceedings of the National Academy of Sciences 113, 11770-11775 (2016). doi:10.1073/pnas.1607171113.",
        "Williams, A. P. et al. Observed impacts of anthropogenic climate change on wildfire in California. Earth's Future 7, 892-910 (2019). doi:10.1029/2019EF001210.",
        "He, Q., Williams, A. P., Johnston, M. R., Juang, C. S. and Wang, B. Influence of time-averaging of climate data on estimates of atmospheric vapor pressure deficit and inferred relationships with wildfire area in the western United States. Geophysical Research Letters 52, e2024GL113708 (2025). doi:10.1029/2024GL113708.",
        "Balch, J. K. et al. The fastest-growing and most destructive fires in the U.S. (2001-2020). Science 386, 425-431 (2024). doi:10.1126/science.adk5737.",
        "Holsinger, L. M., Parks, S. A. and Miller, C. Weather, fuels, and topography impede wildland fire spread in western US landscapes. Forest Ecology and Management 380, 59-69 (2016). doi:10.1016/j.foreco.2016.08.035.",
        "Povak, N. A., Hessburg, P. F. and Salter, R. B. Evidence for scale-dependent topographic controls on wildfire spread. Ecosphere 9, e02443 (2018). doi:10.1002/ecs2.2443.",
        "Balch, J. K. et al. Human-started wildfires expand the fire niche across the United States. Proceedings of the National Academy of Sciences 114, 2946-2951 (2017). doi:10.1073/pnas.1617394114.",
        "Foote, M. The evolution of morphological diversity. Annual Review of Ecology and Systematics 28, 129-152 (1997). doi:10.1146/annurev.ecolsys.28.1.129.",
        "Bookstein, F. L. Morphometric Tools for Landmark Data: Geometry and Biology. Cambridge University Press (1991).",
        "Mitteroecker, P. and Gunz, P. Advances in geometric morphometrics. Evolutionary Biology 36, 235-247 (2009). doi:10.1007/s11692-009-9055-x.",
        "Jolliffe, I. T. and Cadima, J. Principal component analysis: A review and recent developments. Philosophical Transactions of the Royal Society A 374, 20150202 (2016). doi:10.1098/rsta.2015.0202.",
        "Gonzalez, T. F. Clustering to minimize the maximum intercluster distance. Theoretical Computer Science 38, 293-306 (1985). doi:10.1016/0304-3975(85)90224-5.",
        "Efron, B. and Tibshirani, R. J. An Introduction to the Bootstrap. Chapman and Hall/CRC (1993).",
    ]
    for i, ref in enumerate(refs, start=1):
        story.append(p(f"{i}. {ref}", st["small"]))

    story.append(p("Acknowledgments", st["h1"]))
    story.append(p("The author list, acknowledgments, funding sources, and institutional affiliations are placeholders in this draft and must be finalized before submission.", st["small"]))
    story.append(p("<b>Funding:</b> Funding sources to be finalized.", st["small"]))
    story.append(p("<b>Author contributions:</b> Author contribution roles to be finalized.", st["small"]))
    story.append(p("<b>Competing interests:</b> The authors declare no competing interests, pending author confirmation.", st["small"]))
    story.append(p("<b>Data and materials availability:</b> This draft was generated from CubeDynamics Fire VASE workflow artifacts. Public archival links for FIRED-derived inputs, gridMET extraction products, derived analysis tables, and reproducible figure scripts must be added before submission.", st["small"]))
    story.append(p("<b>Supplementary materials:</b> Supplementary Figure 1 contains validation summaries. Supplementary Figure 2 contains the leakage-audited fixed-day prediction benchmark. Derived statistics, figure legends, a data dictionary, and a reproducible figure manifest are packaged under figures/main and figures/supplement.", st["small"]))

    story.append(NextPageTemplate("Figure"))
    story.append(PageBreak())
    figure_paths = prepare_figure_images()
    figures = [
        (
            1,
            figure_paths["figure_1"],
            "Whole-fire histories can be organized in a common developmental coordinate system. Fire VASE converts each real FIRED event into a comparable developmental object by mapping event time from bottom to top and normalized cumulative burned area to ring width. Panel A shows observed fires, pairing each daily cumulative-area history with its corresponding VASE glyph; labels give the descriptive shape name, duration in days, and final burned area in square kilometers. Panel B shows the geometry-only morphospace for all 278,569 fires along the first two developmental gradients. The gray density field is the fire population, darker tones indicate higher density, and red points are high-occupancy real representative fires used as atlas landmarks. Panels C and D evaluate low dimensionality: the scree plot shows individual and cumulative explained variance for the first ten axes, while the null comparison places observed five-axis variance against feature-wise and within-fire growth-timing permutation nulls. Panel E repeats the PCA after excluding increasingly short fires, showing that low-dimensional structure persists but weakens for longer-duration subsets.",
        ),
        (
            2,
            figure_paths["figure_2"],
            "Wildfire occupies a continuous atlas of recurring developmental forms. Panel A places the 18 highest-occupancy real representative Fire VASEs over the full geometry-only density field. Each representative is an observed fire, not an idealized or synthetic glyph; leader lines connect displaced glyphs to their true coordinates along the first two developmental gradients. Panel B ranks representatives by the number of fires closest to each one in the first three gradients, illustrating that some developmental neighborhoods are common whereas others are rare. Panel C shows the coverage curve: as the number of representative fires increases, median and 90th-percentile distance to the nearest representative decline, indicating that a compact atlas can summarize occupied morphospace. Panel D shows real-fire transects through gradients 1, 2, and 3, with glyph shape changing gradually along each axis. Panel E compares local shape-label purity with a class-frequency reference, supporting the use of labels as soft landmarks within a continuous morphospace rather than as sharply separated classes.",
        ),
        (
            3,
            figure_paths["figure_3"],
            "PC1 is a robust but partly redundant developmental profile axis. Panel A shows variance explained by PC1 under feature ablations: the full current feature set, features with scale and duration removed, normalized profile features only, growth-share profiles only, interpolated profile features removed, and fires lasting at least 10 days. Panel B shows cumulative variance in the first five axes for the same ablations. Panel C compares observed first-five-axis variance with null developmental universes that preserve progressively more trivial structure. Feature permutation breaks covariance; stricter nulls preserve final area, duration, zero-growth frequency, observed growth increments, or duration-bin mean profiles. Panel D compares null covariance volume and null-to-observed distance in observed PC1-PC5 space; numbered labels follow the top-to-bottom null order in panel C. The figure supports a reproducible low-dimensional coordinate system but cautions against claiming that observed fires occupy a restricted subset of all plausible trajectories.",
        ),
        (
            4,
            figure_paths["figure_4"],
            "Climate aligns with developmental geometry but does not uniquely determine it. Panel A projects median maximum vapor pressure deficit (VPD, kPa) onto the geometry-first morphospace for 237,235 climate-complete fires; the axes remain the geometry-only developmental gradients from Figure 1. Panel B repeats the projection for average daily high temperature in degrees C, average VPD in kPa, and average wind speed in meters per second, showing that broad climate gradients are visible after the morphospace has been defined. Panel C summarizes held-out linear association models comparing shape recovered from climate and climate recovered from shape under random and region-blocked folds. Error bars show fold variation and blocked results are treated as the conservative comparison. Panel D shows matched real-fire examples that separate similar form from similar climate. Panel E summarizes population-level matched distances, reinforcing that climate and morphology are associated but not interchangeable.",
        ),
    ]
    for fig_no, img, caption in figures:
        story.append(figure_flowable(fig_no, img, caption, st))
        if fig_no != figures[-1][0]:
            story.append(PageBreak())
    return story


def build_pdf() -> dict:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = make_doc(OUTPUT)
    story = build_story()
    doc.build(story)
    report = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "pdf": OUTPUT.as_posix(),
        "source_figures": MAIN_FIGURE_DIR.as_posix(),
        "figures": [
            (FIGURE_DIR / "figure_1.png").as_posix(),
            (FIGURE_DIR / "figure_2.png").as_posix(),
            (FIGURE_DIR / "figure_3.png").as_posix(),
            (FIGURE_DIR / "figure_4.png").as_posix(),
        ],
        "supplementary_figures": [
            (SUPPLEMENT_DIR / "Supplementary_Figure_1_validation.png").as_posix(),
            (SUPPLEMENT_DIR / "Supplementary_Figure_2_prediction.png").as_posix(),
        ],
        "format": "Science initial-submission-style draft: single column, double spaced, line numbered, figures grouped after text",
        "compliance_note": COMPLIANCE_NOTE.as_posix(),
    }
    MANIFEST.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    print(json.dumps(build_pdf(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
