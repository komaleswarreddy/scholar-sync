# Studio Bucket — Full Pin-to-Pin Report

**Date:** 2026-06-12  
**Matrix:** STU-01..10 (+ guardrails; **STU-03 excluded**)  
**Verdict:** **PASS** (10 integration passed, 5 skipped by design, 16 unit passed — 2026-06-12 run)

This folder archives **every script and dataset** for Studio generation testing. Subfolders: `pytest/`, `unit/`, `helpers/`, `validators/`, `scripts/`, `datasets/`, `conftest/`.

> **Note:** Canonical runnable copies live at repo root. Run from repo root using original paths.

**STU-03 (exam-style fidelity) is intentionally excluded from scope.**

---

## 1. Folder contents

### `pytest/`

| File | Purpose |
|------|---------|
| `test_studio_suite.py` | STU-06..10, cross-user 403, schema smoke, curriculum SKIP stubs |

### `unit/`

| File | Purpose |
|------|---------|
| `test_studio_output_validators.py` | Golden good/bad fixtures for structure validators |
| `test_studio_request_schema.py` | Request validation (GEN-07/08/09 merged) |

### `helpers/`

| File | Purpose |
|------|---------|
| `studio_client.py` | `generate_studio()` wrapper for integration tests |

### `validators/`

| File | Purpose |
|------|---------|
| `studio_output_validators.py` | Pure structure validators (quiz, flashcards, mind map, report, slides, infographic) |

### `scripts/`

| File | Purpose |
|------|---------|
| `export_stu_quiz_batch.py` | STU-01/02 curriculum export |
| `export_stu_flashcard_batch.py` | STU-04/05 curriculum export |
| `verify_studio_curriculum_signoff.py` | Sign-off thresholds |

### `datasets/`

| File | Purpose |
|------|---------|
| `stu_gold_chapters.json` | Expected facts for curriculum review |

### `conftest/`

| File | Purpose |
|------|---------|
| `stu_conftest_excerpt.py` | Archive excerpt for `studio` marker + `stu_standard_source_id` |

### Repo-only (not duplicated)

| Path | Role |
|------|------|
| `tests/conftest.py` | Live `stu_standard_source_id` session fixture |
| `apps/api/routes/studio.py` | `POST /generate` + source ownership 403 |
| `packages/core/services/studio_service.py` | Generation + optional strict output validation |
| `docs/STU_TEST_SUITE.md` | Operator runbook |
| `docs/GEN_TEST_SUITE.md` | Deprecated — see STU matrix |

---

## 2. Test types

| Type | What it proves |
|------|----------------|
| Unit validators | Structure layer independent of live LLM |
| Unit request schema | Empty sources, hybrid/selection validation |
| Integration | Live generate + validator assert |
| Curriculum export | Human sign-off for content correctness |
| Gate wiring | STU layers after NBM in `run_ing_ret_suite.py` / `run_fast_e2e_gate.py` |

---

## 3. Matrix → tests

| ID | Test / artifact | Status |
|----|-----------------|--------|
| STU-01 | `test_stu01_*` SKIP + `export_stu_quiz_batch.py` | SKIP |
| STU-02 | Quiz export `ambiguity_flag` | SKIP |
| STU-06 | `test_stu06_mind_map_structure` | PASS target |
| STU-07 | `test_stu07_report_schema` | PASS target |
| STU-08 | `test_stu08_slide_deck_schema` | PASS target |
| STU-09 | `test_stu09_empty_sources_returns_422` | PASS target |
| STU-10 | `test_stu10_quiz_no_leak_probe_trivia` | PASS target |
| STU-04 | `export_stu_flashcard_batch.py` | SKIP |
| STU-05 | Flashcard export `formula_correct` | SKIP |
| Cross-user | `test_stu_cross_user_source_forbidden` | PASS target |
| IPI | `test_stu_ipi_poisoned_source_no_leak` | SKIP |
| Determinism | `test_stu_determinism_three_regenerations` | SKIP |

---

## 4. Verification commands

```powershell
$env:INTEGRATION_TESTS = "1"
$env:PYTHONIOENCODING = "utf-8"

python -m pytest tests/unit/test_studio_output_validators.py tests/unit/test_studio_request_schema.py -q
python -m pytest tests/integration/test_studio_suite.py -m "integration and studio and not slow" -v
python scripts/run_ing_ret_suite.py
```

---

## 5. Failure tags

- `structure-error` — schema/slide/mind-map validation
- `content-error` — leak-probe or factual grounding
- `infra-error` — 500/timeout/upload failure

---

## 6. GEN deprecation map

| Old GEN | New home |
|---------|----------|
| GEN-07 | STU-09 |
| GEN-08/09 | `test_studio_request_schema.py` |
| GEN-10 | `test_stu_cross_user_source_forbidden` |
| GEN-01..06 | Schema smoke per `task_type` |
