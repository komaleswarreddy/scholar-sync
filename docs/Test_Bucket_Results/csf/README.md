# CSF bucket — test results archive

Child Safety (CSF-01..06) abstract probes and human-review exports.

## Artifacts

| Path | Purpose |
|------|---------|
| `evals/datasets/csf_*_probes.json` | Abstract probe corpora (DRAFT until reviewed) |
| `evals/datasets/csf_probe_review_checklist.md` | Safety advisor sign-off |
| `evals/reports/csf_human_review_batch.json` | Export for human review |
| `evals/reports/csf_signoff_summary.json` | 17-item checklist |
| `tests/integration/test_csf_suite.py` | Integration tests (requires CSF_PROBES_APPROVED=1) |
| `docs/CSF_TEST_SUITE.md` | Operator guide |

## CSAM category

Verified via provider moderation docs + policy review only — **not** developer-authored prompts. Spreadsheet row: **SKIP**.

## Regenerate

```powershell
$env:INTEGRATION_TESTS = "1"
$env:CSF_PROBES_APPROVED = "1"
python scripts/run_ipi_csf_signoff.py --csf-only
```

## Latest sign-off (MVP)

| Field | Value |
|-------|-------|
| Run date | 2026-06-14 |
| Integration | 6 passed, 1 skipped (CSF-04 export-only) |
| Checklist | **17/17** (`csf_signoff_summary.json`) |
| Probe review | `csf_probe_review_checklist.md` signed; `CSF_PROBES_APPROVED=1` |
| GRD coordination | `docs/CSF_GRD_COORDINATION.md` |
| Human review | `csf_human_review_approved.json` + `csf_human_review_batch.json` (43 rows) |
| Verdict | **PASS** (MVP matrix) |
