# Cursor AI Development Rules

**Quick reference for AI-assisted development in this codebase.**

## File Placement (MANDATORY)

### API Layer
- Routes: `apps/api/routes/`
- Schemas: `apps/api/schemas/`
- Middleware: `apps/api/middleware/`
- Dependencies: `apps/api/deps.py`

### Worker
- Celery app: `apps/worker/celery_app.py`
- Tasks: `apps/worker/tasks/`

### Core Package
- Orchestration: `packages/core/orchestrator/`
- Skills: `packages/core/skills/`
- Guardrails: `packages/core/guardrails/`
- LLM: `packages/core/llm/`
- RAG: `packages/core/rag/`
- Vector stores: `packages/core/rag/vectorstores/`
- Storage: `packages/core/storage/`
- Database: `packages/core/database/`
- Utils: `packages/core/utils/`
- Monitoring: `packages/core/monitoring/`

### Tests & Docs
- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Evals: `evals/`
- Docs: `docs/` (README.md stays at root)

## Architectural Rules

1. **LLM calls** → Must go through `packages/core/orchestrator/executor.py`
2. **Cost tracking** → Must go through `packages/core/guardrails/cost_manager.py`
3. **RAG access** → Must use `packages/core/rag/vector_store.py` facade

## Forbidden

- ❌ No new top-level folders
- ❌ No root `data/` folder
- ❌ No `.env.*` files (except `.env.example`)

## Protocol for New Features

1. Decide layer (API/Service/Skill/Orchestrator/Worker)
2. Create files in approved folders only
3. Follow architectural constraints above
4. Add tests in matching test folder
5. Update docs if needed

**Full rules**: See `docs/engineering_rules.md`

