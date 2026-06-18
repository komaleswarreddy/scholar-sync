# Generation Test Suite (GEN) — Deprecated

> **Deprecation notice (2026-06-12):** The GEN matrix has been merged into the **Studio bucket (STU-01..10)**. Use [STU_TEST_SUITE.md](STU_TEST_SUITE.md) and [Test_Bucket_Results/studio/README.md](Test_Bucket_Results/studio/README.md) as the canonical operator docs. GEN IDs below are retained for historical traceability only.

**Status:** Superseded by STU. Do not add new GEN-* tests.

Studio generation flows are implemented per [studio three generation flows plan](../.cursor/plans/studio_three_generation_flows_451a8223.plan.md): `sources_only`, `chat_hybrid`, `selection_only` × task types.

## Proposed IDs

| ID | Scope | Verification |
|----|-------|--------------|
| GEN-01 | `sources_only` + mind_map | API 200, structured JSON |
| GEN-02 | `sources_only` + report | Retrieval context used |
| GEN-03 | `chat_hybrid` + report | ~60/40 chat vs source weighting |
| GEN-04 | `selection_only` + flashcards | No retrieval; selection text only |
| GEN-05 | `selection_only` + quiz | Schema validation |
| GEN-06 | Infographic single/multi-source rules | Per product choice in studio service |
| GEN-07 | Empty sources + `sources_only` | 400 with clear message |
| GEN-08 | Hybrid without chat transcript | 400 validation |
| GEN-09 | Selection text too short | 400 validation |
| GEN-10 | Cross-user source isolation | 403 |
| GEN-11 | Rate limit / timeout smoke | Optional load |

## Gate

- Add `scripts/run_gen_gate.py` or extend `run_prod_gate.py` with GEN layers after ING/RET section passes.
- Reuse patterns from `tests/integration/test_retrieval_suite.py` and studio unit tests under `packages/core/services/`.
