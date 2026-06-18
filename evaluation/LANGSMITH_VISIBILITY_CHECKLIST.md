# LangSmith End-to-End Visibility Checklist

Use project from `.env`: **`LANGSMITH_PROJECT`** (currently `notebooklm-dev`).

## One-command publish

```powershell
python scripts/publish_langsmith_full.py --limit 5
```

This uploads datasets, runs experiments with evaluator feedback, and publishes E2E workflow score.

---

## Checklist: what must be visible in LangSmith

### Datasets (left nav → Datasets)

| Item | LangSmith location | How to verify |
|------|-------------------|---------------|
| All 33 agent datasets | `nbm-prompt-{agent_id}` | 33 datasets listed |
| Example count per tier | Dataset → Examples | Tier1=30, Tier2=15, Tier3=5 |
| Input fields | Example → Inputs | Matches `inputs` from JSON |
| Expected outputs | Example → Outputs | `reference_outputs` |
| Variation axis | Example metadata | `variation` (typo, neet, diagram, …) |
| Tags | Example metadata | `tags` (cbse, physics, …) |
| Evaluator name | Example metadata | `evaluator` (router, hint_agent, …) |
| Dataset description | Dataset page | evaluator, models, threshold, hash |

### Tracing → Runs (per experiment)

| Item | Run name pattern | Metadata / outputs |
|------|------------------|-------------------|
| Per-example eval | `eval/{agent}/{example_id}` | agent_name, model, prompt_version |
| Evaluator used | metadata.evaluator | router, query_rewriter, etc. |
| Weighted score | Feedback: `weighted_score` | 0–1 scale |
| Pass/fail | Feedback: `passed` | 1.0 or 0.0 |
| Per-metric scores | Feedback: `metric_*` | intent_accuracy, etc. |
| Input token cost | metadata.input_cost_usd | USD |
| Output token cost | metadata.output_cost_usd | USD |
| Total cost | metadata.total_cost_usd + feedback | USD |
| Token counts | metadata.prompt_tokens, completion_tokens | integers |
| Dataset linkage | metadata.dataset_name, dataset_hash | reproducibility |

### Tracing → Runs (experiment summary)

| Item | Run name pattern | Contents |
|------|------------------|----------|
| Leaderboard row | `experiment/{agent}/{prompt}/{model}` | avg score, pass_rate |
| Winner info | outputs.winner | best prompt+model |
| Models tested | inputs.model | gpt-4o-mini, gpt-4o |
| Prompt versions | inputs.prompt | v1, v2, … |

### Tracing → Runs (E2E)

| Item | Run name | Feedback |
|------|----------|----------|
| Workflow eval | `e2e/workflow_evaluation` | workflow_score, passed |
| Step scores | outputs.runs[].step_scores | router, rewriter, retriever, … |

### Tracing → Runs (live production)

| Item | When | Metadata |
|------|------|----------|
| Setup verify | `verify_langsmith_setup.py` | langsmith_setup_verify |
| Intent classifier | Chat requests | intent_classifier + tokens + cost |
| Health check | `GET /health/langsmith` | API connectivity |

---

## Models & pricing reference

| Model | Input $/1M tokens | Output $/1M tokens |
|-------|-------------------|---------------------|
| gpt-4o-mini | $0.15 | $0.60 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4-turbo | $10.00 | $30.00 |

Source: `config/model_pricing.yaml`

---

## Evaluators mapped to agents

| Evaluator | Agents (examples) | Pass threshold |
|-----------|-------------------|----------------|
| router | intent_classifier, problem_dna_analyzer | 95 |
| query_rewriter | query_rewriter, scope_narrower | 90 |
| retriever | retriever (e2e) | 90 |
| answer_generator | answer_generator (e2e) | 90 |
| verifier | hallucination_guard_retry | 95 |
| formatter | studio_*, direct_chat, OCR | 98 |
| hint_agent | problem solver coaches | 90 |

Full mapping: `config/models.yaml` → `evaluator` field per agent.

---

## Excluded from datasets

- **#7 RAG Chat Response Generator** — see `evals/datasets/prompt_tiered/EXCLUDED_AGENTS.md`

---

## Local mirror reports

After publish, check:

- `evals/reports/langsmith_visibility_report.json`
- `evals/reports/langsmith_datasets_upload.json`
- `evals/reports/experiment_{agent}.json`
- `evals/reports/e2e_workflow_latest.json`

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No runs in LangSmith | `LANGSMITH_TRACING_ENABLED=true`, valid API key |
| Wrong project | Set `LANGSMITH_PROJECT=notebooklm-dev` in `.env` |
| Duplicate dataset examples | Re-run upload (skips existing IDs) or `--force` |
| No cost metadata | Runs need `prompt_tokens`/`completion_tokens` in trace record |
| Cursor MCP | Restart Cursor; OAuth LangSmith MCP for in-IDE queries |
