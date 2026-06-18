# PRF Test Suite — Performance Bucket

**Matrix:** PRF-01 through PRF-07  
**Verdict target:** Harness MVP with smoke in fast gate; full load/soak manual.

## Non-negotiable guardrail

A Performance pass is valid only when ALL hold:

1. **No pre-test restart** — set `PRF_ATTEST_NO_RESTART=1`
2. **Realistic classroom mix** — 70% chat / 20% studio / 10% ingest (`evals/workloads/prf_classroom_v1.json`)
3. **Tail latency** — P50 / P95 / P99 + error rate (never mean alone)
4. **Connection-pool issue** — if `EMAXCONNSESSION` or `max clients reached` appears, status is **OPEN_BUG**, not PASS

## Test matrix

| ID | Name | Smoke threshold | PDF threshold | Runner |
|----|------|-----------------|---------------|--------|
| PRF-01 | Chat TTFT | P95 < 5s | P95 < 3s | `scripts/run_prf_chat_latency.py` |
| PRF-02 | Chat E2E | P95 < 15s | P95 < 8s | same run as PRF-01 |
| PRF-03 | Scoped retrieval | tutor faster | Tutor P95 < 5s | `scripts/run_prf_scoped_retrieval.py` |
| PRF-04 | Ingestion P95 | P95 < 90s | P95 < 30s (10-page) | `scripts/run_prf_ingestion.py` |
| PRF-05 | Studio by type | 2× PDF budget | quiz 12s, flashcards 10s, mind_map 15s, report 25s | `scripts/run_prf_studio_latency.py` |
| PRF-06 | Concurrent load | error < 5% | error < 1%, degradation < 50% | `scripts/run_prf_load.py` |
| PRF-07 | Soak 2–4h | manual | memory growth < 10% | `scripts/run_prf_soak.py` |

## Commands

```powershell
# Terminal 1 — API (no --reload)
.\venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000

# Terminal 2
$env:INTEGRATION_TESTS = "1"
$env:PRF_ATTEST_NO_RESTART = "1"

# Smoke (fast gate subset)
python scripts/run_prf_chat_latency.py --smoke
python -m pytest tests/integration/test_performance_suite.py -m "integration and performance and not slow" -q

# Full manual runs
python scripts/run_prf_chat_latency.py --full
python scripts/run_prf_scoped_retrieval.py --full
python scripts/run_prf_ingestion.py --full --concurrent
python scripts/run_prf_studio_latency.py --full
python scripts/run_prf_load.py --full
python scripts/run_prf_soak.py --duration 2h

# Sign-off checklist
python scripts/verify_prf_signoff.py
```

## Fast E2E gate

After GRD integration:

- `test_performance_suite.py` (not slow)
- Classroom Locust with `PRF_WORKLOAD=1` (70/20/10 mix)

## Failure tags

| Tag | Meaning |
|-----|---------|
| `latency` | P95 over threshold |
| `error_spike` | Error rate over threshold |
| `resource_exhaustion` | RSS/FD trend or soak degradation |
| `harness_artifact` | Client-side bottleneck |
| `open_bug` | Pool exhaustion / 500 under load |

## Artifacts

| Path | Description |
|------|-------------|
| `evals/reports/prf_latest.json` | Merged latest report |
| `evals/reports/prf_baseline.json` | Versioned baseline |
| `evals/reports/prf_chat_latency.json` | PRF-01/02 |
| `evals/reports/prf_load.json` | PRF-06 |
| `evals/reports/prf_signoff_summary.json` | Checklist verifier |

## Gate order

```
fixtures → ING → RET → NBM → STU → GRD → PRF smoke → classroom Locust (PRF-06 adjunct)
```
