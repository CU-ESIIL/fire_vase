# Fire VASE submission freeze

Start with `release_readiness.md`, `manuscript_si_consistency_report.md`, `final_claim_matrix.md`, and `HUMAN_SUBMISSION_CHECKLIST.md`. `claim_source_registry.csv` is the machine-readable authority crosswalk. `freeze_manifest.json` records exact hashes.

Current assembled files are `output/submission/fire_vase_manuscript_submission.pdf` and `output/submission/fire_vase_supplementary_submission.pdf`. The supplied Prism drafts remain unchanged in `docs/manuscripts/fire_vase_developmental_morphology/`.

Regenerate the adversarial package with `PYTHONPATH=src:scripts .venv/bin/python scripts/final_adversarial_pass.py`, assemble PDFs with the bundled PDF runtime and `scripts/assemble_submission_pdfs.py`, then rebuild this freeze with `PYTHONPATH=src:scripts .venv/bin/python scripts/freeze_submission.py`. No external data are downloaded.

Status: **PASS WITH HUMAN ITEMS**. No release or tag was created.
