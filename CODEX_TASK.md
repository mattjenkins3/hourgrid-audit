# Hourgrid Audit — private repository import and verification handoff

**State on 2026-10-13:** Implementation completed and tested in a local Python container; standalone GitHub repository NOT created. The connected GitHub write operation was blocked, so neither code nor ledger changes were pushed. **No public release or social posting authorized.**

## Objective and evidence

Package the independently authored, MIT-licensed `hourgrid-audit` CLI as a private GitHub repository. It provides read-only, explicit timebase integrity audits for hourly energy CSVs. In particular it distinguishes UTC/offset-aware, fixed local standard time and IANA civil time, requires explicit DST `fold` for ambiguous local times, rejects nonexistent spring-forward times, supports hour-ending timestamps, detects missing/duplicate/out-of-order/off-grid hours and optional invalid numeric values, and emits JSON plus an accessible monthly SVG. No data modification or inference. This is a focused pre-model contract checker, not a novel forecasting method or substitute for pvlib/diive.

Verified public context:
- https://docs.python.org/3/library/zoneinfo.html — IANA zone and `fold` semantics.
- https://pvlib-python.readthedocs.io/en/stable/reference/generated/pvlib.iotools.get_nsrdb_psm4_tmy.html — UTC versus local standard time.
- https://github.com/pvlib/pvlib-python/blob/main/docs/examples/irradiance-decomposition/plot_diffuse_fraction.py — hour-ending timestamp handling.
- https://docs.nrel.gov/docs/fy18osti/67399.pdf — NREL SAM weather-file time conventions.

## Contents of the source archive

The attached `hourgrid-audit-build-lab-2026-10-13.zip` contains the complete project under `hourgrid-audit/`: `src/hourgrid_audit/`, `tests/`, `examples/make_example.py`, generated `examples/example-report.json` and `examples/example-coverage.svg`, `scripts/benchmark.py`, `pyproject.toml`, `README.md`, `LICENSE`, `LINKEDIN_DRAFT.md`, and `.github/workflows/test.yml`. Synthetic source CSV is generated locally and deliberately excluded from version control.

## Executed local evidence (not GitHub CI)

Python 3.13.5, 2026-10-13:

```bash
PYTHONPATH=src python -m unittest discover -s tests -q
# Ran 15 tests — OK
PYTHONPATH=src python examples/make_example.py
PYTHONPATH=src python -m hourgrid_audit examples/synthetic_2025.csv \
  --year 2025 --basis fixed --offset-hours -7 --value-column power_kw \
  --report examples/example-report.json --svg examples/example-coverage.svg
# Exit 1 is EXPECTED: 2 missing hours, 1 duplicate, 8758 / 8760 unique hours.
PYTHONPATH=src python scripts/benchmark.py examples/synthetic_2025.csv
# 15 local runs: median approximately 0.038 s (not a comparative benchmark).
```

Tests cover 8760/8784 years, hour-ending rollover, civil DST fold and spring gap, half-hour IANA offset, malformed/nonfinite values, UTC off-grid, ordering, duplicate/missing and CLI exit codes. Real production data have not been tested. No extra billable OpenAI API execution occurred in this run; compute cost and author minutes are unmeasured.

## Single next action

**Import this archive into a newly authorized PRIVATE repository (suggested name `mattjenkins3/hourgrid-audit`, only if available), then run its included GitHub Actions tests on Python 3.10 and 3.13.** Do not publish the repository, change its visibility, post the LinkedIn draft, or mark the ledger as released without explicit owner approval.

Acceptance: all 15 tests pass in target CI, synthetic example exits exactly 1 with `duplicate_hour=1` and `missing_hour=2`, SVG renders correctly, package entrypoint works after `pip install -e .`, README references and license are independently reviewed, and the GitHub ledger is updated as `PRIVATE BUILT / NOT RELEASED`. If a source change is needed, open a private review PR before merging. If subscription Codex is available, use it only for this bounded import/CI task; no separate paid Actions API run is authorized.
