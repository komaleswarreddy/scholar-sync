# Evaluations

Evaluation framework for ScholarSync components.

## Structure

- `datasets/` - Golden datasets for evaluation
  - `prompt_tiered/` - Per-agent prompt optimization datasets (LangSmith-compatible); see `datasets/prompt_tiered/README.md`
- `runners/` - Evaluation runners
- `metrics/` - Evaluation metrics
- `reports/` - Generated evaluation reports

## Usage

```bash
# Agent-level evaluation
python eval.py --agent intent_classifier --prompts v1 --models gpt-4o-mini

# End-to-end workflow
python eval_e2e.py --limit 10

# Legacy retrieval gate
python evals/runners/retrieval_eval.py
```

See [evaluation/README.md](../evaluation/README.md) for the full framework.

