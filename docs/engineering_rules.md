# Engineering Rules & Coding Standards

**Version:** 1.0  
**Date:** January 2025  
**Status:** Active - Mandatory for all code changes

---

## Overview

This document defines the **mandatory** engineering rules and coding standards for the ScholarSync codebase. All code must follow these standards to ensure maintainability, consistency, and architectural integrity.

**This is the single source of truth for file placement and code organization.**

---

## File & Code Placement Rules (MANDATORY)

**⚠️ CRITICAL: When adding any new file, you MUST place it in the approved folder below. Do NOT create new top-level folders without explicit approval.**

### API Layer

- **Routes/controllers**: `apps/api/routes/`
- **Request/response schemas**: `apps/api/schemas/`
- **Middleware**: `apps/api/middleware/`
- **Dependency wiring/DI**: `apps/api/deps.py` (or `apps/api/deps/` if already used)

### Worker

- **Celery app**: `apps/worker/celery_app.py`
- **Background tasks**: `apps/worker/tasks/`

### Core Package

- **Orchestration only**: `packages/core/orchestrator/`
- **Skills** (flashcards/quiz/etc.): `packages/core/skills/`
- **Guardrails** (cost/safety): `packages/core/guardrails/`
- **LLM clients + factory**: `packages/core/llm/`
- **RAG core**: `packages/core/rag/`
- **Vector DB providers**: `packages/core/rag/vectorstores/`
- **Storage providers**: `packages/core/storage/`
- **DB connection/models/migrations**: `packages/core/database/`
- **Shared utilities**: `packages/core/utils/`
- **Monitoring**: `packages/core/monitoring/`

### Tests & Evals

- **Unit tests**: `tests/unit/`
- **Integration tests**: `tests/integration/`
- **Load tests**: `tests/load/`
- **Evals**: `evals/`

### Docs

- **All docs**: `docs/` (only `README.md` stays at repo root)

### Forbidden

- ❌ **Do NOT create new top-level folders**
- ❌ **Do NOT create a root `data/` folder**
- ❌ **Do NOT commit `.env.production/.env.staging/.env.development`** (only `.env.example` allowed)

---

## Creation Protocol for Future Tasks

When implementing any new feature or task, follow this protocol:

### Step 1: Decide Layer First

Before writing code, determine which layer your code belongs to:

- **API route** → `apps/api/routes/`
- **Service** → `packages/core/services/`
- **Skill** → `packages/core/skills/`
- **Orchestrator** → `packages/core/orchestrator/`
- **Worker task** → `apps/worker/tasks/`

### Step 2: Architectural Constraints

Enforce these architectural rules:

1. **All LLM calls must go through** `packages/core/orchestrator/executor.py`
   - Never call LLM clients directly from routes or services
   - Use the orchestrator for all model interactions

2. **All cost usage must go through** `packages/core/guardrails/cost_manager.py`
   - Never write `UsageRecord` directly
   - All cost tracking must use `CostManager`

3. **RAG access must go through** `packages/core/rag/vector_store.py` facade and `vectorstores/` providers
   - Never access vector stores directly
   - Use the facade pattern for all RAG operations

### Step 3: Create Files in Approved Folders

- Create files only inside the approved folders listed above
- Follow existing naming conventions
- Add appropriate `__init__.py` files if needed

### Step 4: Add/Extend Tests

- Add unit tests in `tests/unit/` matching the folder structure
- Add integration tests in `tests/integration/` for cross-layer features
- Ensure tests follow the same placement rules

### Step 5: Update Documentation

- Update relevant docs in `docs/` if the change affects architecture or APIs
- Add inline comments explaining business logic

---

## Code Quality Standards

### General Principles

1. **Readability First**: Code should be self-documenting with clear naming
2. **Comments for Why, Not What**: Explain business logic and complex decisions
3. **DRY (Don't Repeat Yourself)**: Avoid code duplication
4. **SOLID Principles**: Follow object-oriented design principles
5. **Consistent Structure**: Same patterns throughout the codebase

### Type Safety

- Use type hints in Python (`typing` module)
- Use TypeScript types/interfaces in frontend code
- Validate inputs with Pydantic schemas (backend) or Zod (frontend)

### Error Handling

- Use appropriate exception types
- Provide clear error messages
- Log errors with context
- Never expose internal errors to end users

### Testing

- Write tests for all new features
- Maintain >80% code coverage
- Use fixtures and mocks appropriately
- Test edge cases and error conditions

---

## Configuration Management

### Environment Variables

- **Single source of truth**: `config/settings.py`
- Only `.env.example` is committed to repo
- Never commit `.env`, `.env.production`, `.env.staging`, or `.env.development`
- All environment variables must be defined in `config/settings.py`

### Settings Access

- Import settings from `config.settings` (not from environment directly)
- Use `Settings()` instance for all configuration access
- Validate settings at startup

---

## Database & Migrations

### Models

- All models in `packages/core/database/models/`
- Use SQLAlchemy async ORM
- Follow existing naming conventions

### Migrations

- Use Alembic for migrations
- Migration files in `packages/core/database/migrations/versions/`
- Always test migrations up and down
- Never edit existing migration files

---

## API Design

### Routes

- RESTful conventions
- Versioned APIs (`/api/v1/...`)
- Consistent error response format
- Proper HTTP status codes

### Schemas

- Use Pydantic v2 for request/response validation
- Separate request and response schemas
- Document all fields with descriptions

### Middleware

- Authentication/authorization in `apps/api/middleware/auth.py`
- Tenant isolation in `apps/api/middleware/tenant.py`
- Common utilities in `apps/api/middleware/common.py`

---

## References

- **Project Structure**: See `docs/Project_Structure_GenAI.md`
- **API Specification**: See `docs/4_API_Specification.md`
- **Tech Stack**: See `docs/3_Tech_Stack_Architecture.md`

---

## Enforcement

These rules are **mandatory** and enforced through:

1. Code review process
2. Automated linting (where applicable)
3. Architecture validation scripts
4. Documentation in `CURSOR_RULES.md` for AI-assisted development

**Violations of these rules will require refactoring before merge.**

