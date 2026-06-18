# IPI bucket — test results archive

Indirect Prompt Injection (IPI-01..06) harness and reports.

## Artifacts

| Path | Purpose |
|------|---------|
| `tests/fixtures/ipi/` | Versioned poisoned PDF library (TEST-ONLY) |
| `evals/datasets/ipi_cases.json` | Case → fixture mapping |
| `evals/reports/ipi_ingestion_survival.json` | Parser-stripped vs payload-reached |
| `evals/reports/ipi_signoff_summary.json` | 15-item checklist |
| `tests/integration/test_ipi_suite.py` | Integration tests |
| `docs/IPI_TEST_SUITE.md` | Operator guide |

## Regenerate

```powershell
python scripts/run_ipi_csf_signoff.py --ipi-only
# or step-by-step:
python scripts/generate_ipi_fixtures.py
python scripts/log_ipi_ingestion_survival.py
$env:INTEGRATION_TESTS = "1"
python -m pytest tests/integration/test_ipi_suite.py -m "integration and ipi and not slow" -v --junitxml=evals/reports/ipi_pytest.xml
python -m pytest tests/integration/test_ipi_suite.py -m "integration and ipi and slow" -v --junitxml=evals/reports/ipi_pytest_slow.xml
python scripts/verify_ipi_signoff.py --unit-guard-passed
```

## Latest sign-off (MVP)

| Field | Value |
|-------|-------|
| Run date | 2026-06-13 |
| Checklist | **15/15** (`ipi_signoff_summary.json`) |
| Integration | 7 passed, 1 xfailed (metadata parser-stripped), slow persistence passed |
| Verdict | **PASS** (MVP matrix) |
