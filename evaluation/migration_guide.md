# Migration Guide — Evaluation Framework

## From hardcoded prompts/models

### Before

- Prompts: `load_prompt("agents/intent_classifier_system.j2")` directly
- Models: `get_model_for_task("intent_classifier")` hardcoded map in `factory.py`

### After

1. **Prompt versions** live in `prompts/registry.yaml` (+ optional `prompts/{agent}/vN.txt` overrides).
2. **Models** resolve from `config/production.yaml` (prod) or `config/models.yaml` (experiments).
3. Use `load_versioned_prompt("intent_classifier", version="v1", part="system", **kwargs)`.
4. `get_model_for_task()` checks registry first, then falls back to legacy map.

## Step-by-step

### 1. Environment

```env
LANGSMITH_TRACING_ENABLED=true
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=notebooklm-dev
LANGCHAIN_TRACING_V2=true
```

### 2. Register agent in config

Add to `config/models.yaml` and `config/production.yaml`:

```yaml
my_agent:
  task_key: my_task
  model: gpt-4o-mini
  prompt: v1
```

Add to `prompts/registry.yaml`:

```yaml
my_agent:
  v1:
    template: path/to/template.j2
  default: v1
```

### 3. Wire agent code

```python
from packages.core.prompts.versioned_loader import load_versioned_prompt
from packages.core.config.model_registry import get_model, get_prompt_version
from packages.core.observability.langsmith import trace_agent_run

with trace_agent_run("my_agent", inputs={"query": q}, model=get_model("my_agent")) as rec:
    prompt = load_versioned_prompt("my_agent", **template_vars)
    # ... call LLM ...
    rec["output"] = result
```

### 4. Add dataset

Regenerate or hand-edit `evals/datasets/prompt_tiered/.../my_agent.json`, then:

```powershell
python scripts/upload_prompt_tiered_to_langsmith.py --agent my_agent
```

### 5. Run experiments

```powershell
python eval.py --agent my_agent --two-phase
```

### 6. Freeze production

Copy winner from `evals/reports/experiment_my_agent.json` into `config/production.yaml`.

## Backward compatibility

- Existing `load_prompt("studio/quiz_prompt.j2")` calls continue to work.
- Registry override is opt-in via versioned loader + config keys.
- `get_model_for_task` unchanged signature; registry checked first.

## LangSmith visibility checklist

- [ ] `GET /health/langsmith` returns `api_reachable: true`
- [ ] `python scripts/verify_langsmith_setup.py` passes
- [ ] Experiment runs appear in project `notebooklm-dev`
- [ ] Dataset examples uploaded with `upload_prompt_tiered_to_langsmith.py`
- [ ] Human review queues configured per `evaluation/human_review.yaml`

## Rollback

1. Remove agent block from `config/production.yaml`
2. Set `EVAL_USE_PRODUCTION_CONFIG=false`
3. Legacy `factory.py` routing resumes automatically
