# Test report

Command: `PYTHONPATH=src:scripts:. .venv/bin/pytest -q`

- Result: **152 passed, 2 skipped, 125 warnings** in the final full-suite run.
- Collection: complete; no modules excluded and no collection errors.
- Restored contract: `tests/helpers/contracts.py` now enforces time/spatial axes, coordinate validity, nonempty required dimensions, and at least one nonmissing cube value.
- Targeted helper tests: 12 passed.
- New adversarial unit tests: 3 passed.
- Warnings are third-party/deprecation/noninteractive plotting notices, not test failures.
