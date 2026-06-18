# Notebook-Mode Test Suite (NBM-01..06)

Guardrail tests for **exploratory** vs **tutor** notebook modes: strict grounding, global fallback OFF, NCERT scope filters, and mode immutability.

## Pre-flight

1. API on `http://127.0.0.1:8000` **without** `--reload` (gate stability).
2. `INTEGRATION_TESTS=1` and API keys in `.env` (`OPENAI_API_KEY`, `PINECONE_API_KEY`).
3. Database migrated and seeded: `alembic upgrade head`, `python scripts/seed_db.py`.
4. NCERT catalog/index populated (required for NBM-03, NBM-05 tutor tests).
5. **Windows:** set UTF-8 for tutor chats to avoid connection resets on Unicode tracebacks:
   ```powershell
   $env:PYTHONIOENCODING = "utf-8"
   ```

## Run commands

```powershell
python scripts/generate_test_fixtures.py

# Unit (NBM-02 config pins)
python -m pytest tests/unit/test_notebook_mode_config.py -q

# Integration (NBM-01..06 + cross-mode)
python -m pytest tests/integration/test_notebook_mode_suite.py -m "integration and notebook_mode and not slow" -v

# Full ING+RET+NBM gate
$env:INTEGRATION_TESTS = "1"
python scripts/run_ing_ret_suite.py

# Fast E2E gate (includes NBM after RET pytest)
python scripts/run_fast_e2e_gate.py
```

## Leak-probe dataset

- **File:** `evals/datasets/nbm_leak_probe.json` (15 questions).
- Loaded by `nbm_leak_probe_questions` fixture in `tests/conftest.py`.
- Questions are known to LLMs but absent from narrow upload fixtures — answers must be refused, not leaked.

## Test matrix

| ID | Test | Automated | Status | Notes |
|----|------|-----------|--------|-------|
| NBM-01 | `test_nbm01_leak_probe_refuses_without_citations` | Yes | **Pass** | Exploratory: refusal + no citations |
| NBM-02 | `test_nbm02_runtime_no_global_fallback` | Yes | **Pass** | Config + runtime: no global fallback |
| NBM-02 | `test_notebook_mode_config.py` (unit) | Yes | **Pass** | `CHAT_ALLOW_GLOBAL_KNOWLEDGE_FALLBACK=False` |
| NBM-03a | `test_nbm03a_in_scope_question_has_citations` | Yes | **Pass** | Tutor in-scope → citations |
| NBM-03b | `test_nbm03b_leak_probe_blocked_in_tutor_mode` | Yes | **XFAIL** | Refusal OK; citations may linger |
| NBM-03 | `test_nbm03_hybrid_beyond_kb_indicator_in_done_payload` | Yes | **XFAIL** | Hybrid `beyond_kb` not implemented |
| NBM-04 | `test_nbm04_no_general_knowledge_prefix_in_tutor_answer` | Yes | **Pass** | No `General knowledge:` prefix |
| NBM-04 | `test_nbm04_ui_badge_renders_for_beyond_kb` | No (UI) | **Skip** | Manual demo until badge ships |
| NBM-05 | `test_nbm05_retrieved_chunks_within_scope` (×3) | Yes | **Pass** | Trace chunks match scope |
| NBM-05 | `test_nbm05_no_out_of_scope_chapter_in_retrieval` | Yes | **Pass** | Chapter filter in trace |
| NBM-06 | `test_nbm06_mode_unchanged_after_patch` | Yes | **Pass** | Mode unchanged after PATCH |
| NBM-06 | `test_nbm06_mode_change_rejected_with_400` | Yes | **XFAIL** | PATCH ignores `mode` (no 400) |
| Cross | `test_nbm_cross_mode_leak_probe` (×2) | Yes | **Pass / XFAIL** | Exploratory pass; tutor xfail on citations |

**Expected suite outcome:** 12 passed, 1 skipped, 4 xfailed (exit 0).

## Failure tags

Assertion messages use these tags for triage:

| Tag | Meaning |
|-----|---------|
| `boundary-leak` | Model answered from training data instead of sources |
| `indicator-miss` | NBM-04 beyond-KB indicator missing (xfail/skip) |
| `scope-leak` | Retrieved chunk outside declared NCERT scope |
| `infra-error` | 500, timeout, missing trace — skip boundary conclusion |

## 15-item guardrail checklist

| # | Guardrail | Coverage |
|---|-----------|----------|
| 1 | Exploratory refuses leak-probe without citations | NBM-01 (automated) |
| 2 | Global fallback OFF in config | NBM-02 unit (automated) |
| 3 | Global fallback OFF at runtime | NBM-02 integration (automated) |
| 4 | Tutor beyond-KB UI indicator | **Skip** — manual / Phase 2 |
| 5 | Tutor in-scope has citations | NBM-03a (automated) |
| 6 | Tutor off-corpus blocked | NBM-03b (xfail on citations) |
| 7 | Hybrid KB-first + bounded fallback | **XFAIL** — Phase 2 |
| 8 | No `General knowledge:` in tutor text | NBM-04 API (automated) |
| 9 | Scope filters limit retrieval | NBM-05 (automated) |
| 10 | Cross-mode leak-probe (exploratory + tutor) | Cross-mode tests (automated) |
| 11 | Empty / invalid scope handling | Partial — infra skip on failure |
| 12 | Mode unchanged on title PATCH | NBM-06 (automated) |
| 13 | Mode change rejected (400/403) | **XFAIL** — Phase 2 |
| 14 | Trace explain chunks match scope | NBM-05 (automated) |
| 15 | Infra failures tagged, not false leaks | `infra-error` skips (automated) |

## Known product gaps (Phase 2)

Not fixed by this test suite — tracked via xfail/skip:

1. **Server enforce `notebook.mode`** on `/chat/stream` when `notebook_id` is set.
2. **Explicit 400/403** when `mode` is sent on `PATCH /notebooks/{id}`.
3. **Tutor hybrid path** — KB-first + bounded fallback + `answer_origin=beyond_kb` in SSE `done`.
4. **Clear citations on tutor refusal** — currently refusal text with NCERT citations retained.
5. **UI badge** in chat for beyond-KB answers (`ChatInterface.tsx`).
6. **Playwright** for NBM-04 UI and NBM-06 create-flow mode immutability.

## Gate integration

| Script | NBM steps |
|--------|-----------|
| `scripts/run_ing_ret_suite.py` | Config unit + integration after RET |
| `scripts/run_fast_e2e_gate.py` | Same, inside `_run_ing_ret_pytest_layers()` |

Estimated added gate time: ~8–12 minutes (live API + chat streams).

## Files

| File | Role |
|------|------|
| `evals/datasets/nbm_leak_probe.json` | 15 leak-probe questions |
| `tests/unit/test_notebook_mode_config.py` | NBM-02 config pins |
| `tests/integration/test_notebook_mode_suite.py` | NBM-01..06 integration |
| `tests/conftest.py` | `notebook_mode` marker, leak-probe fixture, session scopes |
| `tests/helpers/chat_client.py` | `notebook_id`, `ncert_*` chat params |
