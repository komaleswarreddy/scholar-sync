# Production Gate Scorecard

Generated: 2026-06-11T10:13:44.244557+00:00

Status convention: `indexed` API status = matrix `ready`.

| Test ID | Status | Source | Notes |
|---------|--------|--------|-------|
| ING-01 | PASS | pytest |  |
| ING-02 | KNOWN_GAP | documented | DOCX ingestion not implemented; TXT portion covered by pytest |
| ING-03 | PASS | pytest |  |
| ING-04 | KNOWN_GAP | pytest slow | 50-page synthetic SLA: PASS; 100+ NCERT fixture out of scope |
| ING-05 | PASS | pytest |  |
| ING-06 | PASS | pytest |  |
| ING-07 | PASS | pytest |  |
| ING-08 | PENDING | rubric export | Curriculum sign-off required (≥90%) |
| ING-09 | PASS | pytest |  |
| ING-10 | PASS | pytest slow | 3 TXT latency probe approximates matrix 20-PDF criterion |
| ING-11 | PASS | locust_classroom | 40 users (35 chat stream + 5 upload), 10m sustained; see locustfile_classroom.py |
| RET-01 | PASS | retrieval_eval |  |
| RET-02 | PASS | retrieval_eval |  |
| RET-03 | PASS | retrieval_eval |  |
| RET-04 | FAIL | rubric export | Rubric export failed — re-run after classroom load passes |
| RET-05 | PASS | retrieval_eval |  |
| RET-06 | PASS | retrieval_eval |  |
| RET-07 | PASS | pytest integration |  |
| RET-08 | PASS | retrieval_eval |  |
| RET-09 | PASS | retrieval_eval |  |
| RET-10 | PASS | retrieval_eval |  |
| RET-11 | PASS | retrieval_eval |  |

## Manual sign-off

See [docs/rubrics/CURRICULUM_SIGNOFF.md](rubrics/CURRICULUM_SIGNOFF.md) for ING-08 and RET-04.
