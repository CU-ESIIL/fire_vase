# AI Transparency Statement

Date prepared: 2026-07-22

## Manuscript-ready statement

OpenAI Codex/ChatGPT was used as an AI-assisted coding, analysis, visualization, and editorial tool during development of this project. AI assistance included drafting and revising Python scripts for Fire VASE data ingestion, climate attribution, morphospace analysis, statistical summaries, figure generation, PDF/report production, and render-based quality checks; drafting and revising manuscript text, figure legends, response-to-review material, and simulated reviewer critiques; searching for and organizing candidate citations and author-guideline requirements; and helping maintain logs, manifests, tests, schemas, and documentation. The AI system did not originate the underlying FIRED, MODIS burned-area, gridMET, PRISM, or other observational data, did not make final scientific judgments independently, and is not listed as an author. Human investigators directed the analyses, selected the scientific claims, reviewed code and outputs, verified calculations and citations where reported, and remain responsible for the integrity, interpretation, and final content of the manuscript. Synthetic or illustrative demonstrations created during repository development are documented separately and were not used as evidentiary data for the manuscript analyses.

## Prompt-log basis

The project prompt log documents AI assistance in the following areas:

- Real-data Fire VASE panel generation, including static PDF panels for non-prescribed fires and climate-colored panels for maximum temperature, minimum temperature, vapor pressure deficit, and wind.
- Debugging and correcting climate-color mapping so daily or hourly climate values were represented as developmental rings rather than misleading triangle-wise color variation.
- Building exploratory reports and atlases from real FIRED/gridMET data, including death/ending diagnostics, developmental atlases, size-stratified samples, population summaries, morphology atlases, and climate-vs-shape comparisons.
- Developing Fire VASE data infrastructure, including lakehouse-style tables, schemas, durable climate fields on vase slices, full multi-year gridMET caches, processing manifests, validation reports, and perimeter/extension climate-exposure pilots.
- Writing and revising analysis scripts for morphospace construction, feature extraction, PCA, medoids, null-model audits, climate coupling summaries, leakage-safe prediction baselines, and state-dependent climate analyses.
- Producing figures, figure legends, data dictionaries, manifests, and PDF manuscripts; rendering PDFs to images for visual quality checks; and revising figures to improve readability and remove overlapping labels.
- Drafting manuscript narratives, Science-style manuscript formats, author-guideline compliance notes, response-to-review material, and multiple rounds of simulated editor/reviewer critique followed by manuscript edits.
- Searching for, organizing, and auditing citations, including checking that cited references were real and that claims matched the cited literature where reported.
- Writing repository documentation, tests, examples, and development notes for CubeDynamics and Fire VASE workflows.

The log also records some synthetic or illustrative materials generated for demos, documentation, animations, and example visualizations. Those outputs are separate from the manuscript's evidentiary analyses, which are described as based on real observational fire and climate datasets.

## Responsibility boundary

AI assistance was used to accelerate implementation, synthesis, drafting, review, and quality control. It was not used as an autonomous author, data source, or final scientific authority. The human authors remain responsible for study design, data selection, analytic choices, interpretation, citation accuracy, and all claims in the final manuscript.
