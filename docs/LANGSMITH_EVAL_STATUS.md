# LangSmith Eval — Workspace & Agent Status

**Last updated:** 2026-07-02 (agents 14 + 17 claude reruns complete on shivaprapulsp; both now 9/9)  
**Source of truth for runs:** `Reference dataset/testing_Results.csv`  
**Switch script:** `python scripts/switch_workspace.py <workspace_label>`  
**Run script:** `python scripts/remediate_agents_1_13.py --from-sno <N> --agent <id> ...`

---

## Workspace Registry (All 10 Accounts)

| Label | Gmail | Tenant ID | API Key (suffix) | Status |
|-------|-------|-----------|-----------------|--------|
| `pscmrmindssprint2k25` | pscmrmindssprint2k25@gmail.com | `15d476d5-df92-4760-96b8-52f9130946bf` | `...741f61` | **EXHAUSTED** (trace cap hit) |
| `scombinator26` | scombinator26@gmail.com | `47ca8a69-43eb-4f05-812b-c7778fe6987d` | `...c8ba85` | **EXHAUSTED** (trace cap hit) |
| `emaildam3` | emaildam3@gmail.com | `aafff4b5-45a3-4448-9f7d-805bfc70098d` | `...066ab0` | Available |
| `gra7399` | gra7399@gmail.com | `67272628-c819-44db-bbda-e500db0d6982` | `...431dac` | Available |
| `sui332307` | sui332307@gmail.com | `33d88f33-0349-4117-89c6-5d0d56252773` | `...235cdf` | Available |
| `eskomal66` | eskomal66@gmail.com | `03ba6fa5-eb21-4c9a-9eab-fbf8c26ad03b` | `...605f5f` | Available |
| `cursemes9` | cursemes9@gmail.com | `ac6f370c-8fcd-46f3-a85c-b5cd59a9f2e7` | `...313d48` | Available — assigned agents 18–27 |
| `shivaprapul550` | shivaprapul550@gmail.com | `6fb8fab2-fc02-49fb-ad42-5df052958213` | `...38a7f6` | **EXHAUSTED** — 4727/4750 used (agents 14–17 partial) |
| `sujithgundala97` | sujith.gundala97@gmail.com | `bf982111-f0d4-424f-9520-3605217266b1` | `...d7b81` | Old partial runs — do not use |
| `kumarsujith006` | kumarsujith006@gmail.com | `3ee9feb1-5211-4d8a-b489-69b9933538f3` | `...28977` | Old partial runs — do not use |

> All passwords: `asdfvbnm1234` (except `cursemes9`: `ASDFvbnm1234@`)

**Full API keys** are stored in `scripts/switch_workspace.py` WORKSPACES dict — do not commit to public repos.

---

## How to Switch Workspace

```bash
# Archives current trace_ledger.json, resets budget, patches .env LANGSMITH_API_KEY
python scripts/switch_workspace.py sujithgundala97

# Then run evals
python -m evals.agent_eval.run_matrix --step --agent whole_file_reduce
```

The switch script:
1. Copies current `trace_ledger.json` → `trace_ledger_<label>_<timestamp>.json`
2. Writes a fresh ledger with `used=0` for the new workspace
3. Patches `LANGSMITH_API_KEY` in `.env`
4. Updates `workspace_keys_cache.json`

---

## Agent Completion Status

### ✅ Agents 1–13 — COMPLETE (Workspaces: pscmrmindssprint2k25, scombinator26, emaildam3, gra7399, sui332307, eskomal66, cursemes9)

| # | Agent ID | Workspace | Models Done | Gemini |
|---|----------|-----------|-------------|--------|
| 1 | intent_classifier | pscmrmindssprint2k25 | claude-haiku-4-5, gpt-5-mini, gpt-5.4-mini | — |
| 2 | query_rewriter | scombinator26 | claude-haiku-4-5, gpt-5-mini | ⚠ skipped (503) |
| 3 | query_decomposer | scombinator26 | claude-haiku-4-5, gpt-5-mini | ⚠ skipped (503) |
| 4 | scope_narrower | scombinator26 | claude-haiku-4-5, gpt-5-mini | ⚠ skipped (503) |
| 5 | direct_chat | emaildam3 | gpt-5.4-nano | ⚠ skipped (503) |
| 6 | chat_summarizer | emaildam3 | claude-haiku-4-5 | ⚠ skipped (503) |
| 7 | rag_chat_response_generator | emaildam3 | claude-sonnet-4-6, gpt-5.4 | ⚠ skipped (503) |
| 8 | studio_system_json | gra7399 | gemini-2.5-flash, gpt-5-mini, gpt-5.4-mini | ⚠ partial |
| 9 | studio_quiz | gra7399 | gpt-5-mini, gpt-5.4-mini | ⚠ skipped (503) |
| 10 | studio_flashcards | sui332307 | gpt-5.4-mini | ⚠ skipped (503) |
| 11 | studio_mind_map | sui332307 | claude-haiku-4-5, gpt-5.4-mini | ⚠ partial |
| 12 | studio_slide_deck | sui332307 | gemini-2.5-flash, gpt-5-mini, gpt-5.4 | ⚠ partial |
| 13 | studio_fallback_legacy | eskomal66 | gpt-5.4-nano | ⚠ skipped (503) |

All v1/v2/v3 prompts complete for runtime models. Gemini skipped across all agents (health-check 503/UNAVAILABLE) — re-enable when Gemini API stable by setting `skip_runtime: false` in `evals/agent_eval/agent_models.json`.

---

### ✅ Agents 14–17 — COMPLETE

All 9/9 combos done. Agents 14 and 17 split across two workspaces due to Anthropic limit rerun.

| # | Agent ID | Status | Datasets | Detail |
|---|----------|--------|---------|--------|
| **14** | problem_dna_analyzer | ✅ **9/9 complete** | `6b934edf` (shivaprapul550) + `0ec56467` (shivaprapulsp) | gpt-5.4-mini + gpt-5.4 × v1/v2/v3 on shivaprapul550. claude-sonnet-4-6 × v1/v2/v3 + v3 OpenAI rerun on shivaprapulsp after Anthropic limit fixed. All outputs OK. |
| **15** | whole_file_reduce | ✅ **9/9 complete** | `4c9ac445` (shivaprapul550) | gpt-5.4 + gemini-2.5-flash + gpt-5-mini × v1/v2/v3 = all OK. |
| **16** | whole_file_map_summarizer | ✅ **9/9 complete** | `3f5e8566` (shivaprapul550) | gpt-5.4-mini + gemini-3.1-flash-lite + gpt-5-nano × v1/v2/v3 = all OK. |
| **17** | explain_from_basics | ✅ **9/9 complete** | `991db143` (shivaprapul550) + `9268ee47` (shivaprapulsp) | v1/gpt-5.4 + v1/gemini + v2/gpt-5.4 on shivaprapul550. claude reruns (v1+v2) + v2/gemini + all v3 on shivaprapulsp. Gemini (gemini-3.5-flash) healthy. All outputs OK. |

---

### ⏳ Agents 18–27 — NOT STARTED (Workspace: `cursemes9`)

```bash
python scripts/switch_workspace.py cursemes9
python -m evals.agent_eval.run_matrix --all --agent show_best_approach
# ... one by one per SOP
```

| # | Agent ID | Status |
|---|----------|--------|
| **18** | show_best_approach | ⏳ Not started |
| **19** | show_missing_idea | ⏳ Not started |
| **20** | ncert_document_sketch | ⏳ Not started |
| **21** | help_me_solve_it | ⏳ Not started |
| **22** | problem_solver_followup | ⏳ Not started |
| **23** | tutor_notebook_bootstrap | ⏳ Not started |
| **24** | tutor_follow_up_questions | ⏳ Not started |
| **25** | source_question_extraction | ⏳ Not started |
| **26** | image_ocr | ⏳ Not started |
| **27** | diagram_label_ocr | ⏳ Not started |

---

## Known Issues

| Issue | Agents Affected | Fix |
|-------|----------------|-----|
| Anthropic monthly limit (HTTP 400) — claude-sonnet-4-6 combos produce empty outputs | ~~14, 17~~ **RESOLVED** — reruns completed on shivaprapulsp after limit was fixed | ✅ All claude combos now have valid outputs. |
| LangSmith 429 "Monthly unique traces usage limit exceeded" | shivaprapul550 EXHAUSTED (4727/4750) after agent 17. shivaprapulsp used 2321/5000 (2429 remaining). | Use shivaprapulsp or cursemes9 for remaining agents. |
| Gemini 503/UNAVAILABLE — health-check skips Gemini at runtime | Agents 2–13 (Gemini skipped). Agents 14–16 Gemini ran OK in shivaprapul550 run. | Harness auto-skips at runtime; no action needed. Always attempt Gemini — harness decides. |
| SSL/EOF errors on OpenAI (gpt-4o judge) | Intermittent across all workspaces | Transient — harness retries. Not a blocker. |
| Trace cap hit (5k/month) | workspaces pscmrmindssprint2k25, scombinator26, shivaprapul550 | These are exhausted — never run on them again. Use cursemes9 for remaining agents. |
| sujithgundala97 / kumarsujith006 — old partial runs | 14–21 (old runs) | Do NOT use these workspaces. All agents 14–16 completed fresh on shivaprapul550. Old runs are unreliable. |

---

## Trace Budget Reference

- **Free tier:** 5,000 traces/month per workspace
- **Safety margin:** 250 reserved → **4,750 usable**
- **Each experiment cost:** `N_examples + (N_examples × N_per_eval_evaluators) + N_summary_evaluators`
- **Ledger:** `evals/reports/agent_matrix/trace_ledger.json` — reset automatically on `switch_workspace.py`
- **Exhausted workspaces list:** `evals/reports/agent_matrix/exhausted_workspaces.json`

Check remaining budget before starting a new agent batch:
```bash
python -m evals.agent_eval.run_matrix --status
```

---

## Quick Reference — Resume Commands

```bash
# Run agents 18–27 on cursemes9 (one by one, following the SOP)
# Agents 14–17 are all COMPLETE — no further action needed
python scripts/switch_workspace.py cursemes9
python -m evals.agent_eval.run_matrix --all --agent show_best_approach
# ... repeat for each agent in sequence

# After 2026-08-01: rerun claude-sonnet-4-6 combos for agents 14 and 17
# (need to set up a fresh workspace or verify shivaprapul550/cursemes9 budget)
```

---

## testing_Results.csv Update

`testing_Results.csv` is updated manually after each agent completes.

**Current CSV state (as of 2026-07-02):** Agents 1–17 rows fully updated. Agents 14–17 all show 9/9 session links across both workspaces. Agents 18–27 rows are stale until each run completes.
