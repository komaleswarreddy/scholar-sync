# Bucket — Test Script Archive (ING / RET / NBM / STU / GRD)

This folder holds **copies of every `.py` test script we ran** for ingestion, retrieval, notebook-mode guardrails, studio generation, and guardrails, plus a detailed `README.md` in each bucket.

> **Note:** Canonical runnable copies live at repo root (`tests/`, `scripts/`, `evals/`, `testsprite_tests/`). Files here are an **archive** for pin-to-pin documentation. Run from repo root using original paths.

## Folders

| Bucket | Scripts | README |
|--------|---------|--------|
| [ingestion/](ingestion/) | 26 `.py` files | [ingestion/README.md](ingestion/README.md) |
| [retrieval/](retrieval/) | 27 `.py` files | [retrieval/README.md](retrieval/README.md) |
| [notebook/](notebook/) | 7 `.py` files + 1 dataset | [notebook/README.md](notebook/README.md) |
| [studio/](studio/) | 9 `.py` files + 1 dataset + validators | [studio/README.md](studio/README.md) |
| [guardrails/](guardrails/) | 8 `.py` files + 4 datasets + product fixes | [guardrails/README.md](guardrails/README.md) |
| [performance/](performance/) | PRF runners, helpers, Locust mix | [performance/README.md](performance/README.md) |

## Layout (each bucket)

```
ingestion/  or  retrieval/  or  notebook/
├── README.md           Full pin-to-pin report
├── pytest/             Integration test .py
├── unit/               Unit test .py
├── helpers/            chat_client.py (notebook only)
├── conftest/           NBM fixture excerpt (notebook only)
├── datasets/           nbm_leak_probe.json (notebook only)
├── load/               Locust .py (ingestion only)
├── eval/               retrieval_eval.py (retrieval only)
├── testsprite/         TestSprite ING-*.py or RET-*.py
└── scripts/            Gate runners, rubric export, fixture scripts
```

## Verdict (2026-06-13)

| Bucket | Matrix | Result |
|--------|--------|--------|
| Ingestion | ING-01..11 | **9 PASS**, 2 KNOWN_GAP |
| Retrieval | RET-01..11 | **11 PASS** |
| Notebook mode | NBM-01..06 | **9 PASS**, 1 SKIP, 4 XFAIL |
| Studio | STU-01..10 (no STU-03) | **8 PASS**, 6 SKIP (curriculum/IPI/slow) |
| Guardrails | GRD-01..07 | **8 PASS**, 2 SKIP (red-team, judge cal) |
| Performance | PRF-01..07 + sign-off | **3 PASS**, 3 XFAIL, 2 PARTIAL |
| Cross-bucket | TestSprite + Fast E2E | TestSprite **15/23**; Fast E2E **PASS** |

Spreadsheet: [Test_Bucket_Results_Summary.xlsx](Test_Bucket_Results_Summary.xlsx) (71 rows + Summary sheet).

Full report: [../PRODUCTION_TEST_REPORT.md](../PRODUCTION_TEST_REPORT.md)  
Notebook runbook: [../NBM_TEST_SUITE.md](../NBM_TEST_SUITE.md)  
Studio runbook: [../STU_TEST_SUITE.md](../STU_TEST_SUITE.md)  
Guardrails runbook: [../GRD_TEST_SUITE.md](../GRD_TEST_SUITE.md)
