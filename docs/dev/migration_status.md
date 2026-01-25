# Project Restructuring Migration Status

## ✅ Completed

1. **Directory Structure Created**
   - `config/` - Created with settings.py, models.yaml, slo.yaml
   - `apps/api/` - Routes, middleware, schemas directories created
   - `apps/worker/` - Directory created
   - `packages/core/` - All subdirectories created (guardrails, orchestrator, rag, llm, storage, database, services, etc.)
   - `evals/`, `tests/`, `infrastructure/` - Directories created

2. **Config Migration**
   - ✅ `backend/app/core/config.py` → `config/settings.py`
   - ✅ Created `config/models.yaml` and `config/slo.yaml`

3. **Database Migration**
   - ✅ `backend/app/core/database.py` → `packages/core/database/connection.py`
   - ✅ All models moved to `packages/core/database/models/`
   - ✅ Updated imports in models

4. **LLM Migration**
   - ✅ All LLM code moved to `packages/core/llm/`
   - ✅ `base.py` renamed to `_base.py`
   - ✅ Updated imports

## 🔄 In Progress / Remaining

### Critical Files to Move:

1. **Services** (`backend/app/services/` → `packages/core/services/`)
   - [ ] `chat.py` → `chat_service.py`
   - [ ] `notes.py` → `note_service.py`
   - [ ] `studio.py` → `studio_service.py`
   - [ ] `ingestion.py` → `source_service.py`
   - [ ] `rag.py` → Move to `packages/core/rag/`
   - [ ] `vector.py` → Move to `packages/core/rag/vectorstores/pinecone_store.py`
   - [ ] `storage.py` → Move to `packages/core/storage/`
   - [ ] `text_processing.py` → Move to `packages/core/rag/chunker.py` or `packages/core/utils/`

2. **API Routes** (`backend/app/api/v1/endpoints/` → `apps/api/routes/`)
   - [ ] `chat.py`
   - [ ] `notes.py`
   - [ ] `sources.py`
   - [ ] `studio.py`
   - [ ] Create `health.py`

3. **Middleware** (`backend/app/core/middleware.py` → `apps/api/middleware/`)
   - [ ] Split into `tenant.py`, `auth.py`, `common.py`
   - [ ] Move `backend/app/core/auth.py` → merge into `apps/api/middleware/auth.py`

4. **Schemas** (`backend/app/schemas/` → `apps/api/schemas/`)
   - [ ] `chat.py`
   - [ ] `source.py`
   - [ ] `studio.py`
   - [ ] Create `base.py` and `notes.py`

5. **Prompts** (`backend/app/prompts/` → `packages/core/prompts/`)
   - [ ] Move all prompt files
   - [ ] Update template paths

6. **Main Application** (`backend/app/main.py` → `apps/api/main.py`)
   - [ ] Move and update all imports

7. **Placeholder Files to Create**
   - [ ] `packages/core/guardrails/` - All files
   - [ ] `packages/core/orchestrator/` - All files
   - [ ] `packages/core/skills/` - All files
   - [ ] `packages/core/rag/` - embedder.py, retriever.py, chunker.py, vector_store.py
   - [ ] `packages/core/storage/` - base.py, s3.py, local.py
   - [ ] `apps/worker/` - celery_app.py and tasks
   - [ ] Other missing components

8. **Import Updates**
   - [ ] Update ALL imports across all moved files
   - [ ] Fix circular dependencies
   - [ ] Update test imports

9. **Scripts**
   - [ ] Move `backend/scripts/` → `scripts/`
   - [ ] Update paths in scripts

## 📝 Import Path Mapping

Old → New:
- `app.core.config` → `config.settings`
- `app.core.database` → `packages.core.database.connection`
- `app.models.*` → `packages.core.database.models.*`
- `app.core.llm.*` → `packages.core.llm.*`
- `app.services.*` → `packages.core.services.*`
- `app.api.v1.endpoints.*` → `apps.api.routes.*`
- `app.core.middleware` → `apps.api.middleware.*`
- `app.schemas.*` → `apps.api.schemas.*`
- `app.prompts.*` → `packages.core.prompts.*`

## ⚠️ Important Notes

1. **Do NOT delete old files yet** - Keep both until migration is complete and tested
2. **Update imports incrementally** - Fix imports as files are moved
3. **Test after each major move** - Ensure no broken imports
4. **Create placeholders** - For components that don't exist yet, create minimal stubs with TODOs


