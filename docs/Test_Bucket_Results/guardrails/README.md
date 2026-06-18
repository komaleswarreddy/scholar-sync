# Guardrails Bucket — Full Pin-to-Pin Report

**Date:** 2026-06-12  
**Matrix:** GRD-01 through GRD-07 (+ red-team export + judge calibration)  
**Verdict:** **PASS** target for automated subset; red-team export **SKIP** until human sign-off

Archive of scripts, datasets, and pytest modules for the Guardrails bucket. Run from repo root using canonical paths.

---

## 1. Folder contents

### `pytest/`

| File | Purpose |
|------|---------|
| `test_guardrails_suite.py` | GRD-01..07 integration tests |

### `unit/`

| File | Purpose |
|------|---------|
| `test_academic_integrity.py` | GRD-01 pattern unit tests |
| `test_pii_detector_indian.py` | GRD-04 Aadhaar / +91 |
| `test_rate_limiter_shared.py` | GRD-06 singleton accumulation |
| `test_prompt_injection_protection.py` | GRD-05 (excerpt — 5 dataset samples) |

### `helpers/`

| File | Purpose |
|------|---------|
| `guardrails_client.py` | `stream_guardrail_check`, `post_chat_raw` |
| `guardrails_judge.py` | Behavior-based refusal / bypass judges |

### `datasets/`

| File | Purpose |
|------|---------|
| `grd_must_refuse.json` | Adversarial prompts per GRD category |
| `grd_must_allow.json` | Legitimate look-alikes |
| `grd_injection_prompts.json` | 20 injection prompts |
| `grd_pii_synthetic.json` | Synthetic PII + non-PII controls |

### `scripts/`

| File | Purpose |
|------|---------|
| `export_grd_redteam_batch.py` | Live export for human red-team review |
| `verify_grd_signoff.py` | Bypass / over-refusal thresholds |
| `run_ing_ret_suite.py` | Gate excerpt — GRD unit + integration after STU |

### Product fixes (repo root)

| Path | GRD |
|------|-----|
| `packages/core/memory/rate_limiter.py` | GRD-06 `get_rate_limiter()` singleton |
| `apps/api/routes/chat.py` | Uses shared limiter |
| `packages/core/security/pii_detector.py` | GRD-04 Indian PII |
| `packages/core/security/academic_integrity.py` | GRD-01 cheating patterns |
| `packages/core/langgraph/chat_graph.py` | Pipeline wiring |

---

## 2. Gate order

```
fixtures → ING → RET → NBM → STU → GRD unit → GRD integration (not slow) → retrieval_eval
```

---

## 3. Failure tags

| Tag | Meaning |
|-----|---------|
| `bypass` | Harmful answer or forbidden substring in response |
| `over-refusal` | Legitimate prompt incorrectly refused |
| `infra-error` | 5xx, health failure, missing retry_after |
| `judge-error` | Export classifier disagreement |

---

## 4. Operator runbook

See [../../GRD_TEST_SUITE.md](../../GRD_TEST_SUITE.md).
