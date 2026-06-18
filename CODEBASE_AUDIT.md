# ScholarSync (NotebookLM) — Complete Codebase Audit

**Generated:** 2026-06-03  
**Method:** Exhaustive static analysis (Option C feature slices + Option D file appendix). No runtime execution.  
**Scope:** ~540 tracked files; all source, config, docs, scripts, tests, plans reviewed via parallel deep dives.

**Use this document** when you ask for changes later — it maps product intent → code paths → known gaps.

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [System architecture](#2-system-architecture)
3. [Feature slice: Auth & tenancy](#3-feature-slice-auth--tenancy)
4. [Feature slice: Sources & ingestion](#4-feature-slice-sources--ingestion)
5. [Feature slice: Chat & RAG](#5-feature-slice-chat--rag)
6. [Feature slice: Tutor / NCERT mode](#6-feature-slice-tutor--ncert-mode)
7. [Feature slice: Studio generation](#7-feature-slice-studio-generation)
8. [Feature slice: Notes](#8-feature-slice-notes)
9. [Feature slice: Admin & analytics](#9-feature-slice-admin--analytics)
10. [Feature slice: Security pipeline](#10-feature-slice-security-pipeline)
11. [Feature slice: Infrastructure & config](#11-feature-slice-infrastructure--config)
12. [API reference (mounted)](#12-api-reference-mounted)
13. [Frontend routes & state](#13-frontend-routes--state)
14. [Database schema](#14-database-schema)
15. [Prompts & policies](#15-prompts--policies)
16. [Tests & scripts](#16-tests--scripts)
17. [Documentation hierarchy](#17-documentation-hierarchy)
18. [Known gaps, dead code, drift](#18-known-gaps-dead-code-drift)
19. [Q&A cheat sheet](#19-qa-cheat-sheet)
20. [Appendix D: Complete file inventory](#20-appendix-d-complete-file-inventory)

---

## 1. Executive summary

**ScholarSync** is an enterprise-style **NotebookLM clone for schools**: upload PDFs, chat with RAG over sources, generate Studio artifacts (quiz, flashcards, mind map, report, slides, infographic), tutor mode with NCERT corpus, and admin analytics.

| Layer | Technology | Location |
|-------|------------|----------|
| Monorepo | pnpm + Turborepo | Root `package.json`, `turbo.json` |
| Frontend | Next.js 14 App Router, Clerk, TanStack Query | `apps/web` (~129 files) |
| API | FastAPI, async SQLAlchemy | `apps/api` (29 Python files) |
| Domain / RAG | Python 3.11+, LangGraph, LlamaIndex adapters | `packages/core` (~147 Python + 27 `.j2`) |
| Shared TS types | Zod (unused by web today) | `packages/types` |
| Vectors | Pinecone + OpenAI embeddings | `packages/core/rag/vectorstores` |
| DB | PostgreSQL (Supabase-compatible) | 2 Alembic migrations, 9 core tables + NCERT |
| Storage | Supabase Storage (S3-compatible client) | `packages/core/storage/s3.py` |
| Auth | Clerk JWT | Middleware in API + web |
| Tenancy | Subdomain → `tenants` row | **Not** `X-Tenant-ID` header |

**Production paths:** Chat = `LangGraphChatPipeline`; Studio = `StudioService` (not `packages/core/skills/*`, which are stubs).

---

## 2. System architecture

```mermaid
flowchart TB
  subgraph client [apps/web Next.js]
    UI[Dashboard / Tutor / Studios / Analytics]
    API_CLIENT[api-client.ts axios + SSE fetch]
  end

  subgraph api [apps/api FastAPI]
    MW[TenantMiddleware + Clerk JWT]
    R_CHAT[/api/v1/chat/*]
    R_INGEST[/api/v1/ingest/*]
    R_STUDIO[/api/v1/studio/*]
    R_ADMIN[/api/v1/admin/*]
    R_METRICS[/api/v1/metrics/*]
  end

  subgraph core [packages/core]
    LG[LangGraphChatPipeline]
    ST[StudioService]
    ING[IngestionService + LlamaIndexIngestionAdapter]
    RET[Retriever + RAG agents]
    SEC[Security chain]
  end

  subgraph external [External services]
    PG[(PostgreSQL)]
    PC[(Pinecone)]
    OAI[OpenAI LLM + embeddings + moderation]
    COH[Cohere rerank]
    SB[Supabase Storage + optional Postgres]
    RD[(Redis - sketch cache / planned Celery)]
  end

  UI --> API_CLIENT --> MW
  MW --> R_CHAT --> LG
  MW --> R_STUDIO --> ST
  MW --> R_INGEST --> ING
  LG --> RET --> PC
  ST --> RET
  ING --> PC
  LG --> OAI
  ST --> OAI
  RET --> COH
  ING --> SB
  MW --> PG
  LG --> PG
```

**Request path (chat):** Browser SSE → `POST /api/v1/chat/stream` → `LangGraphChatPipeline.stream()` → moderation → memory/cache → dialog route → intent → retrieval/whole-file → grounding gates → generate → moderation output → evaluator → cache store.

**Request path (studio):** `POST /api/v1/studio/generate` → `StudioService.generate()` → Pinecone multi-query retrieval → `load_prompt(studio/*.j2)` → LLM JSON/markdown.

---

## 3. Feature slice: Auth & tenancy

### Backend (`apps/api/middleware/tenant.py`, `auth.py`)

| Concern | Implementation |
|---------|----------------|
| **User** | `Authorization: Bearer` Clerk JWT → `request.state.user_id` = `sub` |
| **Tenant** | `Host` subdomain `*.scholarsync.com`; localhost → `default` |
| **Tenant ID** | DB lookup `Tenant.subdomain` → UUID (`request.state.tenant_id`), 5 min cache |
| **User sync** | Upsert `User` by `clerk_user_id` or email on auth |
| **Admin** | `User.role == "admin"` via `check_admin_role()` in admin routes |
| **Dev** | JWT optional on metrics/dashboards; `DEV_TENANT_ID` fallback |

**Not used:** `X-Tenant-ID` for resolution (CORS allows it; web sends cookie/header but API ignores for tenant lookup).

### Frontend (`apps/web/src/middleware.ts`, `UserContext.tsx`)

- Clerk protects routes; subdomain sets `tenantId` cookie + `x-tenant-id`.
- `apiClient` sets `Authorization`, `x-tenant-id`, `x-user-id`.
- **Hardcoded admin email** on `/` and `/dashboard` redirects (real gate is backend `is_admin`).

---

## 4. Feature slice: Sources & ingestion

### API

| Endpoint | Handler |
|----------|---------|
| `POST /api/v1/ingest/upload` | Quick upload + `BackgroundTasks` → `IngestionService.process_file_background` |
| `GET /api/v1/ingest/sources` | List sources |
| `DELETE /api/v1/ingest/sources/{id}` | Delete source + vectors |

### Core (`packages/core/services/source_service.py`)

1. Upload to **Supabase Storage** (`S3Storage`) — key `{tenant_id}/{source_id}.pdf`
2. PDF extract + `PDFPreprocessor`
3. **`LlamaIndexIngestionAdapter`**: chunk → optional **contextual retrieval** (sketch + per-chunk context) → embed → **Pinecone** namespace = normalized `tenant_id`
4. Metadata: `source_id`, `tenant_id`, page, text
5. `Source` row: `status`, `chunks_count`, `user_id` (Clerk string)

**Isolation:** Same Pinecone namespace per tenant; filter by `source_id` in queries (not per-user namespace).

### Frontend (`SourceList.tsx`, `SourceContext`)

- Multi-select sources → `localStorage` `selected_source_ids`
- Poll upload status; optional auto map-reduce summary after upload

---

## 5. Feature slice: Chat & RAG

### API entry

- **Stream:** `POST /api/v1/chat/stream` — SSE `chunk`, `citation`, `done`, `error`
- **CRUD:** chats, messages, feedback, summarize
- **NCERT filters:** `GET /api/v1/chat/ncert-filters`

### LangGraph (`packages/core/langgraph/chat_graph.py`)

| Node / branch | Purpose |
|---------------|---------|
| `ModerationInput` | OpenAI moderation + safety |
| `Memory` / `CacheCheck` | Summary + answer cache |
| `DialogRoute` | `should_skip_rag` → direct chat |
| `IntentClassify` | LLM intent → security_block / whole_file / retrieval |
| `Retrieval` | `Retriever.retrieve_with_agents` (Phase 2) |
| `WholeFileMapReduce` | Pinecone list/fetch all chunks for one source |
| `ContextGroundingGate` | Block weak evidence |
| `TutorRelevanceGate` / `SourceRelevanceGate` | NCERT + source score floors |
| `Generate` | `rag_prompt.j2` or `direct_chat.j2` |
| `ModerationOutput` / `Evaluator` / `CacheStore` | Output checks + metrics |

### Retrieval stack (`packages/core/rag/retriever.py`)

**Phase 2 agents (when `USE_RETRIEVAL_AGENTS`):** IntentClassifier → ScopeNarrower → QueryRewriter → QueryDecomposer (gated) → Pinecone → BM25/hybrid fusion → **Cohere rerank** → MMR → ContextSelector.

**Supporting:** `context_aware_weighting`, `hallucination_guard` (post-gen), `RestrictedRetriever` for approved sources only.

### Dual “intent” systems

1. **`IntentGate`** (regex, `security/intent_gate.py`) — academic-only pre-LLM
2. **`IntentClassifier`** (LLM JSON, `rag/agents/intent_classifier.py`) — routing incl. `security_block`

---

## 6. Feature slice: Tutor / NCERT mode

### NCERT global corpus (admin)

- **DB:** `ncert_global_documents`, `ncert_global_ingestion_runs`
- **Storage:** `global/ncert/{document_id}.pdf`
- **Pinecone namespace:** `NcertDataGlobal` (configurable)
- **Ingest:** `ncert_global_service.process_ncert_upload_background` — larger embeddings, NCERT metadata (`class`, `subject`, `chapter_no`, …)
- **Validation:** `config/ncert_subjects_by_class.yaml`

### Chat / tutor retrieval

- When `include_ncert_global` + flags: merge tenant sources + NCERT hybrid retrieval
- **Tutor relevance:** `tutor_relevance.max_relevance_vs_chunks` gates weak NCERT matches
- **Web:** `/tutor` → `/tutor-mode`; filters from API + `ncertSubjectsByClass.ts` fallback

### API admin (`admin_ncert_global.py`)

Upload, list, delete cascade, ingestion runs, subjects-by-class.

---

## 7. Feature slice: Studio generation

### API

`POST /api/v1/studio/generate` → `StudioService.generate()` + `trace_id` in `pipeline_trace` store.

### Task types (`task_type`)

| Task | Prompt template | Output shape |
|------|-----------------|--------------|
| `quiz` | `studio/quiz_prompt.j2` | JSON |
| `flashcards` | `studio/flashcards_prompt.j2` | JSON |
| `mind_map` | `studio/mind_map_prompt.j2` | JSON/markdown |
| `slide_deck` | `studio/slide_deck_prompt.j2` | Structured |
| `report` | `studio/report_prompt.j2` | Markdown (`report_format` variants) |
| `infographic` | `infographic_structured_prompt.j2` | **Requires exactly 1 source** |

### Context modes

- `sources_only` — Pinecone over `source_ids`
- `chat_hybrid` — transcript fraction + source chunks
- `selection_only` — selected text only, no Pinecone

### Frontend

- `StudioSuite` + `StudioGenerationContext` → `GenerationModal` + per-type displays
- Outputs also in `localStorage` `generatedStudioFeatures`; hub at `/studios`

**Note:** `packages/core/skills/*.py` are **unimplemented stubs**; all logic is in `StudioService`.

---

## 8. Feature slice: Notes

| API | Service |
|-----|---------|
| `/api/v1/notes` CRUD | `NotesService` |

**Frontend:** `NotesSection` on dashboard; `/notes` library with bookmark/generated filters (`noteFlagsV1` in localStorage). Draft save modal on navigation.

---

## 9. Feature slice: Admin & analytics

### API groups

- **`/api/v1/admin`:** users, Clerk backfill, `me/flags`, per-user/aggregate metrics, sessions
- **`/api/v1/admin/ncert-global/*`:** NCERT corpus (see §6)
- **`/api/v1/metrics`:** summary, RAG quality, tokens, cost, cache, latency, agents, logs, reset
- **`/api/v1/dashboards`:** aliases to metrics handlers
- **`/api/v1/pipeline-traces`:** recent, detail, **`/{id}/explain`** (admin RAG explainer)

### Frontend `/analytics/*`

Users, documents, NCERT global, queries, RAG metrics, agents, guardrails, endpoints, cost-tokens, alerts, logs, pipeline. Gated by `getMyAdminFlags()`.

**Duplicate:** `/dashboard/analytics` uses raw axios (legacy); primary is `/analytics`.

---

## 10. Feature slice: Security pipeline

**Order in LangGraph chat:**

1. OpenAI Moderation (input/output)
2. `SafetyFilter` (keywords)
3. `PromptInjectionDetector`
4. `IntentGate` (regex)
5. `PIIDetector` (redact)
6. LLM `IntentClassifier` (`security_block`)
7. `RestrictedRetriever` (optional)
8. `context_grounding_gate`
9. `tutor_relevance` / source relevance
10. `prompt_integrity` on compiled prompt
11. `hallucination_guard` post-generate
12. `RefusalTemplates`

**Upload:** `file_validator.py`  
**Guardrails package:** `CostManager` active; `InputGuardian` / `OutputModerator` / `BudgetEnforcer` mostly TODO.

---

## 11. Feature slice: Infrastructure & config

### Docker (`docker-compose.yml`)

| Service | Role |
|---------|------|
| `postgres` | DB `scholarsync` |
| `redis` | Broker/cache DB 0 |
| `api` | Uvicorn `apps.api.main:app` |
| `worker` | **Broken:** `celery_app` not instantiated (commented TODO) |

### Config (`config/settings.py`)

Single Pydantic `Settings` — 100+ tunables (RAG flags, NCERT, moderation, Redis sketch cache, eval flags). **`.env.example` lists only a subset.**

### Other config files

| File | Used by |
|------|---------|
| `models.yaml` | `cost_manager.py` |
| `ncert_subjects_by_class.yaml` | NCERT admin + chat filters |
| `metrics_schema.json` | `monitoring/alerts.py` |
| `slo.yaml` | **Documentation only** (no code loader) |

### `infrastructure/`

Terraform, Kubernetes, Helm — **empty placeholders** (`.gitkeep` only).

### `evals/`

**Scaffold only** — `BaseEvalRunner` empty; `scripts/run_evals.py` **missing**.

### Worker (`apps/worker/`)

| File | Status |
|------|--------|
| `celery_app.py` | Celery import present; **app not created** |
| `tasks/pdf_task.py`, `cleanup_task.py`, `usage_aggregation.py` | Task stubs |

Background work today: FastAPI `BackgroundTasks` on upload routes, not Celery.

---

## 12. API reference (mounted)

**Entry:** `apps.api.main:app`  
**~70 HTTP endpoints** (incl. duplicate `/health`, `/` on main + health router).

| Prefix | Router file | Main capabilities |
|--------|-------------|-------------------|
| `/api/v1/chat` | `chat.py` | SSE stream, NCERT filters, chat CRUD, summarize, feedback |
| `/api/v1/ingest` | `sources.py` | Upload, list, delete sources |
| `/api/v1/studio` | `studio.py` | Generate artifacts |
| `/api/v1/notes` | `notes.py` | Notes CRUD |
| `/api/v1/metrics` | `metrics.py` | Observability + agents + reset |
| `/api/v1/dashboards` | `dashboards.py` | Dashboard aliases |
| `/api/v1/alerts` | `alerts.py` | Alert status |
| `/api/v1/admin` | `admin.py`, `admin_ncert_global.py` | Admin + NCERT |
| `/api/v1/pipeline-traces` | `pipeline_traces.py` | Trace inspection |

**Not mounted (dead):** `routes/debug.py` (`/retrieval_trace`), `CORSWrapperMiddleware`.

**Streaming:** Only `POST /api/v1/chat/stream` (SSE). No WebSockets.

---

## 13. Frontend routes & state

### Routes

| Path | Purpose |
|------|---------|
| `/` | Auth router → `/home`, `/analytics`, or `/sign-in` |
| `/dashboard` | **Main workspace** (sources \| chat \| studio+notes) |
| `/tutor`, `/tutor-mode` | Tutor hub + full-screen tutor chat |
| `/studios` | Studio gallery |
| `/notes` | Notes library |
| `/analytics/*` | Admin metrics (12 sub-pages) |
| `/sign-in`, `/sign-up` | Clerk |

**No per-notebook URL** — single workspace per tenant user.

### State patterns

| Pattern | Usage |
|---------|--------|
| React Context | Chat, Source, User, Theme, StudioGeneration, StudioChatBridge |
| TanStack Query | `useChats`, `useSources`, `useNotes` |
| localStorage | `selected_source_ids`, `generatedStudioFeatures`, `noteFlagsV1`, theme, telemetry |
| Zustand | In `package.json` but **unused** |

### API client (`api-client.ts`)

- Base: `NEXT_PUBLIC_API_URL` or `http://localhost:8000`
- SSE: native `fetch` to `/api/v1/chat/stream`
- 401 circuit breaker → logout after 3 failures

**Types drift:** Web does **not** import `@scholarsync/types`; duplicates interfaces locally.

---

## 14. Database schema

**Migrations:** `0001_initial_schema` → `0002_ncert_global_knowledge` (Supabase RLS hardening on all tables).

```
Tenant 1──* Source, Chat, Note
Chat 1──* Message
NcertGlobalDocument 1──* NcertGlobalIngestionRun
User (standalone, Clerk-linked, no tenant FK)
GuardrailUserBlock, AlertUserSession → tenant_id
```

**Vectors live in Pinecone**, not Postgres.

---

## 15. Prompts & policies

| Location | Count | Loader |
|----------|-------|--------|
| `packages/core/prompts/templates/**/*.j2` | 27 | `load_prompt()` |
| `packages/core/prompts/policies/chat_policy.default.yaml` | 1 | `knowledge/policy_loader.py` |
| `docs/used_prompts/**/*.md` | 22 mirrors | Manual sync expected |

**In code but not mirrored in docs:** `document_sketch.j2`, `ncert_document_sketch.j2`, `chunk_contextualization.j2`.

**Legacy / weak wiring:** `infographic_prompt.j2` (use structured), `whole_file_map_prompt.j2` (map phase often inline), `scope_narrower` templates (agent may use inline prompts).

---

## 16. Tests & scripts

### Pytest (`tests/`)

**14 unit modules** covering: retrieval strategy, grounding, hallucination guard, intent security block, moderation, injection, chat policy YAML, studio schema/context, RAG prompt structure.

**Gaps:** No HTTP integration tests; no `Retriever`/Pinecone E2E in CI; `conftest` DB fixture TODO; `tests/integration/` empty.

**Root scripts:** `test_tutor_mode_filtering.py`, `test_phase1.py` (manual/ad hoc).

### Scripts (`scripts/` — 36 files)

| Category | Examples |
|----------|----------|
| Dev setup | `init_db.py`, `seed_db.py`, `start_backend.bat` |
| Smoke | `smoke_chat_flow.py`, `smoke_contextual_retrieval.py` |
| Verification | `verify_imports.py`, `final_verification_test.py` |
| Incident/debug | `test_openai_*.py`, `fix_openai_proxies.py` |
| Redis/sketch | `redis_ping.py`, `redis_sketch_smoke.py` |
| Legacy cleanup | `cleanup_backend.sh` |

---

## 17. Documentation hierarchy

**Authority (when specs conflict):**

1. `SOURCE_OF_TRUTH_PRODUCT_SPEC.md` — living V1 product spec  
2. `IMPLEMENTED_FEATURES_AND_WORKFLOWS.md` — code-grounded matrix (2026-05-29)  
3. `docs/1`–`docs/6` — historical MVP/FRD/API/design (some stale ✅/⏳)  
4. `docs/*_FLOW.md` — chat + studio flows (generally accurate for LangGraph)  
5. Root `*_FIX_SUMMARY.md` — incident logs (may overlap/contradict)

**Cursor plans (`.cursor/plans/`):** 13 plans — LlamaIndex RAG, LangGraph chat, contextual retrieval, studio traces, NCERT admin, quality hardening, etc.

---

## 18. Known gaps, dead code, drift

### Broken / missing code

| Issue | Detail |
|-------|--------|
| `StudioFeature` model | `studio_feature_service.py` imports missing model |
| `packages.core.cache.sketch_store` | Referenced by ingestion; **module missing** |
| Celery worker | `apps/worker/celery_app.py` not wired; Docker worker will fail |
| `evals/` + `run_evals.py` | Scaffold only |

### Dead / unused in API

- `routes/debug.py` not mounted  
- `deps.get_current_tenant_id` / `get_current_user_id` unused  
- `CORSWrapperMiddleware` not registered  
- `schemas/notes.py` vs inline models in `routes/notes.py`  
- Duplicate `/health`, `/`

### Frontend

- `CitationModal` orphaned  
- `zustand` unused dependency  
- Hardcoded `ADMIN_EMAILS`  
- `/dashboard/analytics` duplicate of `/analytics`

### Integrations

- **Gemini:** disabled in `factory.py`  
- **Cohere:** rerank only; no fallback if key missing  
- **skills/ package:** all stubs

### Doc drift

- `docs/6` still says "Cricket Academy"  
- `AGENTIC_RAG_AGENTS.md` references removed `rag_service.py`  
- Multiple root fix summaries for same 401/httpx/Gemini issues  
- PRD vs SOURCE_OF_TRUTH vs IMPLEMENTED_FEATURES status badges may differ

---

## 19. Q&A cheat sheet

| Question | Where to look |
|----------|----------------|
| Add a new API endpoint? | `apps/api/routes/`, register in `main.py`, schemas in `apps/api/schemas/` |
| Change chat behavior? | `packages/core/langgraph/chat_graph.py`, `chat_state.py`, `rag/retriever.py` |
| Change RAG retrieval? | `retriever.py`, `rag/agents/*`, `retrieval_strategy.py`, settings flags |
| Change studio output? | `studio_service.py`, `prompts/templates/studio/*.j2` |
| Change upload/ingestion? | `source_service.py`, `llama_adapters/ingestion.py`, `contextual_retrieval/*` |
| NCERT admin/upload? | `ncert_global_service.py`, `admin_ncert_global.py`, `config/ncert_subjects_by_class.yaml` |
| Security refusal text? | `security/refusal_templates.py`, moderation in `chat_graph.py` |
| Tenant resolution? | `middleware/tenant.py` (Host subdomain, not header) |
| Frontend chat UI? | `ChatInterface.tsx`, `api-client.ts` `streamChat` |
| Frontend studio? | `StudioGenerationContext.tsx`, `StudioSuite.tsx`, `GenerationModal.tsx` |
| DB model change? | `packages/core/database/models/`, new Alembic under `migrations/versions/` |
| Env var default? | `config/settings.py` (+ update `.env.example`) |
| Cost tracking? | `guardrails/cost_manager.py`, `config/models.yaml` |
| Metrics/alerts? | `monitoring/metrics.py`, `alerts.py`, `config/metrics_schema.json` |
| Prompt doc mirror? | Edit `.j2` + matching `docs/used_prompts/**/*.md` |

---

## 20. Appendix D: Complete file inventory

**Total tracked files:** ~540 (per workspace glob).  
**Classification below** — every top-level area included; per-file detail for primary source trees.

### Root (non-source highlights)

| File / pattern | Type | Purpose |
|----------------|------|---------|
| `README.md` | Doc | Main onboarding |
| `CODEBASE_AUDIT.md` | Doc | This audit |
| `SOURCE_OF_TRUTH_PRODUCT_SPEC.md` | Spec | Authoritative product V1 |
| `IMPLEMENTED_FEATURES_AND_WORKFLOWS.md` | Spec | Feature matrix vs code |
| `CURSOR_RULES.md` | Rules | AI dev placement rules |
| `ALL_FIXES_SUMMARY.md`, `ERROR_FIXES_SUMMARY.md`, … | Incident | Fix narratives (11 files) |
| `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml` | Build | JS monorepo |
| `pyproject.toml`, `requirements.txt` | Build | Python package + Docker deps |
| `turbo.json`, `tsconfig.json` | Build | Turborepo + TS paths |
| `alembic.ini` | DB | Migration config |
| `docker-compose.yml`, `docker-compose.test.yml` | Infra | Dev/test stacks |
| `Dockerfile.api`, `Dockerfile.worker` | Infra | Container images |
| `Makefile` | Infra | Dev shortcuts |
| `.env.example` | Config | Env template (subset) |
| `test_phase1.py`, `test_tutor_*.py`, `.bat` | Test | Ad hoc scripts |
| `check_ncert_chapters.py` | Script | NCERT utility |
| `backend.log`, `generated-*.txt` | Generated | Runtime artifacts |
| `.cursor/plans/*.plan.md` | Plan | 13 feature plans |
| `cache/` | Runtime | Local caches |

### `apps/` (~129 files)

#### `apps/api/` (29 Python)

`main.py`, `deps.py`, `__init__.py`  
`middleware/`: `auth.py`, `tenant.py`, `request_logging.py`, `common.py`, `cors_wrapper.py`, `__init__.py`  
`routes/`: `chat.py`, `sources.py`, `studio.py`, `notes.py`, `health.py`, `metrics.py`, `dashboards.py`, `alerts.py`, `admin.py`, `admin_ncert_global.py`, `pipeline_traces.py`, `debug.py`, `__init__.py`  
`schemas/`: `base.py`, `chat.py`, `source.py`, `studio.py`, `notes.py`, `ncert_global.py`, `__init__.py`

#### `apps/web/` (~100 TS/TSX + configs)

`package.json`, `next.config.js`, `tsconfig.json`, `tailwind.config.ts`, `postcss.config.js`, `.eslintrc.json`, `next-env.d.ts`  
`src/middleware.ts`  
`src/app/`: layout, providers, globals.css, page, home, dashboard/*, tutor/*, studios, notes, analytics/* (12 pages), (auth)/*  
`src/components/`: ui (5), layout (6), chat (7), studio (11), sources (2), notes (5), analytics (3), index  
`src/contexts/`: 6 contexts  
`src/hooks/`: 5 hooks  
`src/lib/`: 7 modules  
`src/config/`: `ncertSubjectsByClass.ts`

#### `apps/worker/` (6 Python)

`celery_app.py`, `__init__.py`  
`tasks/`: `pdf_task.py`, `cleanup_task.py`, `usage_aggregation.py`, `__init__.py`

### `packages/` (~183 files)

#### `packages/types/` (3)

`package.json`, `tsconfig.json`, `src/index.ts` (Zod: Source, ChatMessage, Citation, StudioTaskType, Quiz, Flashcard, Note)

#### `packages/core/` (~147 Python + 27 `.j2` + 1 YAML)

| Folder | Files (count) | Role |
|--------|---------------|------|
| `compliance/` | 4 | Audit, retention, privacy |
| `database/` | 16 | connection, models×8, migrations×2 |
| `evaluation/` | 5 | Evaluator, confidence, cold start, scheduler |
| `guardrails/` | 6 | Budget, cost, input/output guardians |
| `image/` | 2 | DALL·E client |
| `knowledge/` | 2 | Chat policy loader |
| `langgraph/` | 3 | Chat pipeline + state |
| `llm/` | 5 | OpenAI client, factory |
| `memory/` | 9 | Cache, summarizer, rate limit, compression |
| `monitoring/` | 6 | Metrics, alerts, pipeline trace, SLO |
| `orchestrator/` | 5 | Context builder, executor (TODO) |
| `policies/` | 2 | Policy enforcer stub |
| `processing/` | 4 | PDF preprocess, semantic chunk, context cache |
| `prompts/` | 3 + templates | loader, registry, 27 `.j2`, 1 yaml policy |
| `rag/` | 25+ | retriever, chunker, embedder, agents×14, contextual×3, llama×3, rerank, vectorstores×4 |
| `security/` | 12 | Full security chain |
| `services/` | 7 | chat, source, notes, studio, ncert, studio_feature |
| `skills/` | 9 | Stubs |
| `storage/` | 4 | base, local, s3 (Supabase) |
| `utils/` | 5 | exceptions, files, formatting, tokens |

### `config/` (7)

`settings.py`, `models.yaml`, `slo.yaml`, `ncert_subjects_by_class.yaml`, `metrics_schema.json`, `__init__.py`

### `docs/` (70)

- Specs `1`–`6`, flows×7, `used_prompts/`×23, dev×2, architecture guides×10+, phase docs×3, audit reports×10+, misc

### `scripts/` (36)

Listed in §16.

### `tests/` (20)

`conftest.py`, `unit/`×13, `integration/` (empty), `load/locustfile.py`, `test_studio_retrieval_merge.py`

### `evals/` (7)

Scaffold: `runners/base_eval.py`, placeholders for datasets/reports/metrics

### `infrastructure/` (4)

Empty terraform/k8s/helm placeholders + `__init__.py`

---

## Maintenance note

When you request changes, cite this doc section + file paths. After substantive edits, update:

- Relevant `docs/*_FLOW.md` or `IMPLEMENTED_FEATURES_AND_WORKFLOWS.md`
- Matching `docs/used_prompts/` if prompts change
- This file’s §18 if new gaps are introduced or fixed

---

*End of audit.*
