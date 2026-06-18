# Performance Bucket — Full Pin-to-Pin Report

**Date:** 2026-06-13  
**Matrix:** PRF-01 through PRF-07  
**Verdict:** **Harness complete — local smoke XFAIL/PARTIAL** (no OPEN_BUG pool; PDF thresholds need staging)

Post-sprint artifacts: `evals/reports/prf_baseline.json`, `prf_latest.json` (merged XFAIL), `prf_signoff_summary.json` (16/16 checklist with `--allow-partial`). Spreadsheet updated in `Test_Bucket_Results_Summary.xlsx`.

| Case | Local result | Notes |
|------|--------------|-------|
| PRF-01/02 | XFAIL | TTFT/E2E P95 ~83s vs smoke budget; 0% errors |
| PRF-03 | XFAIL | Tutor not faster than exploratory on slow box |
| PRF-04 | PASS | Ingest P95 ~38s |
| PRF-05 | PASS | 6 studio types smoke |
| PRF-06 | PARTIAL | 429 from GRD_TEST_RPM=10; no pool exhaustion |
| PRF-07 | PARTIAL | 2m RSS sampler (+6.6%); full 2–4h not run |

Orchestrator: `scripts/run_prf_all.py --quick --with-load --with-soak`.

Archive of scripts, helpers, workloads, and pytest modules for the Performance bucket. Run from repo root using canonical paths.

---

## 1. Folder contents

### `pytest/`

| File | Purpose |
|------|---------|
| `test_performance_suite.py` | PRF smoke + manual SKIP stubs for load/soak |

### `helpers/`

| File | Purpose |
|------|---------|
| `performance_stats.py` | P50/P95/P99, baselines, OPEN_BUG detection, report schema |
| `performance_client.py` | Timed chat/studio/ingest clients |

### `workloads/`

| File | Purpose |
|------|---------|
| `prf_classroom_v1.json` | Frozen 70/20/10 classroom mix |

### `scripts/`

| File | Purpose |
|------|---------|
| `run_prf_all.py` | Orchestrate smoke/full suite + merge + signoff |
| `run_prf_chat_latency.py` | PRF-01 / PRF-02 |
| `run_prf_scoped_retrieval.py` | PRF-03 |
| `run_prf_ingestion.py` | PRF-04 |
| `run_prf_studio_latency.py` | PRF-05 |
| `run_prf_load.py` | PRF-06 |
| `run_prf_soak.py` | PRF-07 scaffold |
| `prf_resource_sampler.py` | RSS sidecar for soak |
| `verify_prf_signoff.py` | 16-item checklist validator |

### `load/`

| File | Purpose |
|------|---------|
| `locustfile_classroom.py` | Extended with StudioStudentUser + PRF 70/20/10 weights |

---

## 2. Guardrails (from XLSX)

1. **NO pre-test restart** — `PRF_ATTEST_NO_RESTART=1` required for manual runners
2. **Report P50/P95/P99 + error rate** — never mean alone
3. **Connection-pool / 500 = OPEN bug** until proven fixed under realistic load
4. **Instrument resources over time** — `prf_resource_sampler.py` for soak
5. **Document environment** — every report includes `environment` block
6. **Versioned baseline** — `evals/reports/prf_baseline.json`

---

## 3. Gate order

```
fixtures → ING → RET → NBM → STU → GRD → PRF smoke → classroom Locust (PRF_WORKLOAD=1)
```

---

## 4. Failure tags

| Tag | Meaning |
|-----|---------|
| `latency` | Threshold exceeded |
| `error_spike` | Error rate too high |
| `resource_exhaustion` | Memory/FD trend |
| `harness_artifact` | Client bottleneck |
| `open_bug` | EMAXCONNSESSION / pool exhaustion |

---

## 5. Canonical paths (repo root)

All runnable code lives at repo root — this folder is documentation archive only:

- `tests/integration/test_performance_suite.py`
- `tests/helpers/performance_*.py`
- `scripts/run_prf_*.py`
- `evals/workloads/prf_classroom_v1.json`

See [`docs/PRF_TEST_SUITE.md`](../../PRF_TEST_SUITE.md) for commands.
