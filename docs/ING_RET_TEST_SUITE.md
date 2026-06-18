# ING + RET Production Test Suite

Full pin-to-pin TestSprite vs layered gate analysis: [PRODUCTION_TEST_REPORT.md](PRODUCTION_TEST_REPORT.md).

End-to-end test coverage for ingestion (ING-01..ING-11) and retrieval (RET-01..RET-11).

## Prerequisites

1. API running at `http://127.0.0.1:8000` (or set `NOTEBOOKLM_API_URL`)
2. `.env` with `DATABASE_URL`, `OPENAI_API_KEY`, `PINECONE_API_KEY`, storage credentials
3. `INTEGRATION_TESTS=1`

## Quick start (demo gate)

```powershell
python scripts/generate_test_fixtures.py
$env:INTEGRATION_TESTS = "1"
python scripts/run_ing_ret_suite.py
```

## Production gate (full matrix)

Run API **without** `--reload` (indexing is unstable with reload):

```powershell
# Terminal 1
.\venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000

# Terminal 2
$env:INTEGRATION_TESTS = "1"
python scripts/run_prod_gate.py
```

Outputs:

- `evals/reports/prod_gate_scorecard.json`
- `docs/PROD_GATE_SCORECARD.md`
- `evals/reports/ing08_rubric_batch.json` (ING-08, **PENDING**)
- `evals/reports/ret04_rubric.json` (RET-04, **PENDING**)

Expand golden set before eval:

```powershell
python scripts/expand_golden_set.py
```

## Test matrix

| ID | Automated | Location | Notes |
|----|-----------|----------|-------|
| ING-01 | Yes | `tests/integration/test_ingestion_suite.py` | Upload + chat top-3 citations; `indexed` = ready |
| ING-02 | Partial | same | TXT only; DOCX = **KNOWN_GAP** |
| ING-03 | Yes | same + `test_pdf_upload_validator.py` | Sync password validation |
| ING-04 | Partial (slow) | same | 50-page synthetic passes; 100+ NCERT = **KNOWN_GAP** |
| ING-05 | Yes | same | 4xx, no 500 |
| ING-06 | Yes | same + `test_file_validator.py` | .exe/.mp4/.zip blocked |
| ING-07 | Yes | same | Distinct source IDs |
| ING-08 | Rubric | `scripts/export_ing08_batch.py` | **PENDING** manual ≥90%; see `docs/rubrics/CURRICULUM_SIGNOFF.md` |
| ING-09 | Yes | same | Image-only PDF clear error |
| ING-10 | Yes (slow) | same | P95 latency budget |
| ING-11 | Load | `tests/load/locustfile.py` | 5-user burst upload (spawn-rate 5, 60s; pool-safe) |
| RET-01 | Yes | `evals/runners/retrieval_eval.py` | Recall@k |
| RET-02 | Yes | same | MRR |
| RET-03 | Yes | same | Context precision |
| RET-04 | Rubric | `scripts/rubric_ret04_citation_check.py` + `evals/datasets/ret04_questions.txt` | **PENDING** manual ≥95% |
| RET-05 | Yes | eval runner | Multi-doc top-5 |
| RET-06 | Yes | integration + eval | Refusal rate |
| RET-07 | Yes | `test_retrieval_suite.py` | Cross-user 403 |
| RET-08 | Yes | eval runner | Paraphrase Jaccard |
| RET-09 | Yes | eval runner | Formula subset |
| RET-10 | Yes | eval runner | Per question_type |
| RET-11 | Yes | eval runner | Long questions |

## TestSprite

With API running:

1. Ensure `.testsprite/config.json` exists or run bootstrap once
2. `testsprite_generate_backend_test_plan` with project path
3. `testsprite_generate_code_and_execute` with `serverMode=development`

## Demo vs prod gates

- **Demo gate**: `pytest -m "integration and not slow"` (via `run_ing_ret_suite.py`)
- **Fast E2E** (~15–30 min): `python scripts/run_fast_e2e_gate.py` — ingestion + retrieval pytest + `retrieval_eval` + short classroom Locust
- **Prod gate** (launch): `python scripts/run_prod_gate.py` — full unit + demo + slow pytest + `retrieval_eval` + rubric exports + Locust + TestSprite + scorecard

### Status convention

The API returns `status: "indexed"` when ingestion is complete. The test matrix calls this **ready**; they are equivalent in reports and scorecards.

### Documented gaps (KNOWN_GAP)

See [DEMO_SCOPE_DEFERRALS.md](DEMO_SCOPE_DEFERRALS.md) for explicit demo-scope deferrals and user-facing errors.

| Test ID | Gap |
|---------|-----|
| ING-02 | DOCX ingestion not implemented |
| ING-04 | No real 100+ page NCERT fixture; 50-page synthetic used |

### Independent verification

See [INDEPENDENT_VERIFICATION.md](INDEPENDENT_VERIFICATION.md) (TestSprite ≥18/23, secondary to local gate).

```powershell
python scripts/run_testsprite_local.py
```

Run when the API is idle (not during RET-04 export or classroom Locust).

### RET-04 rubric export

```powershell
$env:RET04_SOURCE_ID = "<indexed-source-uuid>"  # optional: skip re-upload
python scripts/run_prod_gate.py --only ret04_rubric
```

`ret04_questions.txt` has 50 lines but **20 unique** factual prompts (padded from golden set). The exporter dedupes automatically. Resume with incremental writes to `evals/reports/ret04_rubric.json`.

### Classroom load (ING-11)

`tests/load/locustfile_classroom.py` — 40 users (35 chat + 5 upload), 10 minutes sustained. Set `GATE_CLASSROOM_SHORT=1` for a 2-minute smoke.

## Thresholds

Configured in `evals/datasets/retrieval_golden.json` → `thresholds`.
