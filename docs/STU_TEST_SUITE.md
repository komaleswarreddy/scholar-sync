# Studio Test Suite (STU-01..10)

Structure and guardrail tests for **Studio generation** (`POST /api/v1/studio/generate`): quiz, flashcards, mind map, report, slide deck, infographic.

**STU-03 (exam-style fidelity) is intentionally excluded from scope** — no tests, spreadsheet rows, or export scripts.

## Pre-flight

1. API on `http://127.0.0.1:8000` without `--reload`.
2. `INTEGRATION_TESTS=1` and `.env` keys (`OPENAI_API_KEY`, `PINECONE_API_KEY`).
3. `python scripts/generate_test_fixtures.py`
4. **Windows:** `$env:PYTHONIOENCODING = "utf-8"`

## Run commands

```powershell
python scripts/generate_test_fixtures.py

# Unit (validators + request schema + mind map grounding)
python -m pytest tests/unit/test_studio_output_validators.py tests/unit/test_studio_request_schema.py tests/unit/test_studio_mind_map_grounding.py tests/unit/test_studio_mind_map_retrieval_batch.py tests/unit/test_studio_service_context_modes.py tests/test_studio_retrieval_merge.py -q

# Frontend/backend static contract (no JS test runner)
python scripts/verify_mind_map_studio_contract.py

# Integration (automated STU rows; curriculum rows SKIP)
python -m pytest tests/integration/test_studio_suite.py -m "integration and studio and not slow" -v

# Full gate (ING + RET + NBM + STU)
$env:INTEGRATION_TESTS = "1"
python scripts/run_ing_ret_suite.py

# Curriculum export (manual path)
python scripts/export_stu_quiz_batch.py
python scripts/export_stu_flashcard_batch.py
python scripts/verify_studio_curriculum_signoff.py
```

## Test matrix

| ID | Coverage | Automated | Initial status |
|----|----------|-----------|----------------|
| STU-01 | Quiz answer-key correctness | Export + human | **SKIP** |
| STU-02 | MCQ non-ambiguity | Export JSON fields | **SKIP** |
| STU-06 | Mind map structure | `validate_mind_map_structure` | **PASS** target |
| STU-MMP | Mind map NotebookLM source-only grounding | Unit + contract script + integration | **PASS** target |
| STU-07 | Report schema + attribution heuristic | `validate_report` | **PASS** target |
| STU-08 | Slide deck schema | `validate_slide_deck` | **PASS** target |
| STU-09 | Empty `sources_only` → 422 | Request + integration | **PASS** target |
| STU-10 | Leak-probe guard on quiz | Integration | **PASS** target |
| STU-04 | Flashcard fact integrity | Export + human | **SKIP** |
| STU-05 | Flashcard formula correctness | Export + human | **SKIP** |
| Guardrail | Cross-user source 403 | Integration | **PASS** target |
| Guardrail | IPI poisoned source | Skipped | **SKIP** |
| Guardrail | 3× determinism | `@pytest.mark.slow` | **SKIP** |

**Merged from deprecated GEN:** GEN-07 → STU-09; GEN-08/09 → `test_studio_request_schema.py`; GEN-10 → cross-user 403; GEN-01..06 → schema smoke per task type.

## Failure tags

| Tag | Meaning |
|-----|---------|
| `structure-error` | JSON/markdown/slide schema invalid |
| `content-error` | Grounding leak or factual issue |
| `infra-error` | 500, timeout, upload failure — skip boundary conclusion |

## Curriculum workflow (STU-01/02/04/05)

1. Pre-author expected facts in `evals/datasets/stu_gold_chapters.json`
2. Run export scripts against live API
3. Reviewer fills `human_verified`, `correctness`, `ambiguity_flag` / `formula_correct`
4. `verify_studio_curriculum_signoff.py` enforces STU-01 ≥95%, STU-04 ≥95%, STU-05 ≥98%

## Pin-to-pin bucket report

See [Test_Bucket_Results/studio/README.md](Test_Bucket_Results/studio/README.md).
