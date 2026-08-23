# ScholarSync — End-to-End Project Guide (Interview Ready)

**ScholarSync** is an enterprise-grade **AI Notebook platform for schools**. Think of it as a NotebookLM-style product, purpose-built for education: multi-tenant workspaces, RAG chat over uploaded sources, NCERT tutor mode, a guided problem solver, Studio study assets (quiz / flashcards / mind maps / slides), admin ops dashboards, and safety guardrails.

This README is written so you can **explain the project in an interview from beginner → professional**, without skipping architecture, data flow, or trade-offs.

---

## Table of contents

1. [Elevator pitch (30 seconds)](#1-elevator-pitch-30-seconds)
2. [Problem & product](#2-problem--product)
3. [Who uses it (personas)](#3-who-uses-it-personas)
4. [High-level architecture](#4-high-level-architecture)
5. [Monorepo map](#5-monorepo-map)
6. [Tech stack](#6-tech-stack)
7. [Request lifecycle (one chat message)](#7-request-lifecycle-one-chat-message)
8. [Multi-tenancy](#8-multi-tenancy)
9. [Authentication & authorization](#9-authentication--authorization)
10. [Data model (core entities)](#10-data-model-core-entities)
11. [Source ingestion pipeline](#11-source-ingestion-pipeline)
12. [RAG system (deep dive)](#12-rag-system-deep-dive)
13. [LangGraph chat orchestration](#13-langgraph-chat-orchestration)
14. [Feature deep dives](#14-feature-deep-dives)
15. [Security & guardrails](#15-security--guardrails)
16. [Frontend architecture](#16-frontend-architecture)
17. [Backend API surface](#17-backend-api-surface)
18. [Workers & async jobs](#18-workers--async-jobs)
19. [Config, env, and feature flags](#19-config-env-and-feature-flags)
20. [Eval / quality system (LangSmith)](#20-eval--quality-system-langsmith)
21. [Testing strategy](#21-testing-strategy)
22. [Local setup & run](#22-local-setup--run)
23. [Deployment mental model](#23-deployment-mental-model)
24. [Interview talking points & common questions](#24-interview-talking-points--common-questions)
25. [Glossary](#25-glossary)
26. [Further docs](#26-further-docs)
27. [License](#27-license)

---

## 1. Elevator pitch (30 seconds)

> ScholarSync is a **multi-tenant educational AI notebook**. Schools get isolated workspaces. Students upload PDFs/notes, then chat with those sources using a production **RAG + LangGraph** pipeline with grounding gates, citations, and safety filters. On top of that we ship **NCERT tutor mode**, a **coaching-style problem solver**, and **Studio** tools that generate quizzes, flashcards, mind maps, and slide decks — plus an **admin portal** for users, costs, RAG quality, and guardrails.

**One-liner for senior interviews:**  
*“FastAPI + LangGraph backend, Next.js App Router frontend, Postgres for OLTP, Pinecone namespaces for vector isolation, Redis for cache/queue, Clerk-legacy → platform JWT auth, and a LangSmith agent-eval matrix for prompt/model bake-offs.”*

---

## 2. Problem & product

### Problem

Schools want AI study tools that:

- Stay **grounded in the school’s own materials** (not hallucinated internet answers)
- Respect **curriculum boundaries** (especially NCERT / syllabus lock)
- Are **safe for minors** (moderation, PII, prompt-injection, academic integrity)
- Scale across **many schools** without data leakage between tenants
- Give operators **visibility** (cost, latency, retrieval quality)

### Product answer

| Capability | What the student / school gets |
|------------|--------------------------------|
| Notebooks + sources | Upload PDFs/text/links → chunk → embed → retrieve |
| RAG chat | Streaming Q&A with citations and relevance gates |
| Tutor mode | NCERT-backed chapter bootstrap + follow-ups |
| Problem solver | Multi-mode coaching (explain / help solve / missing idea / best approach) |
| Studio | Quizzes, flashcards, mind maps, slide decks from sources |
| Notes | Rich notes tied to the workspace |
| Admin / teacher portals | Users, NCERT global docs, metrics, guardrails, exams |

---

## 3. Who uses it (personas)

```
┌─────────────┐   ┌──────────────┐   ┌────────────────┐
│   Student   │   │   Teacher    │   │ School Admin / │
│  notebook,  │   │ exams,       │   │ Ops portal     │
│  tutor, PS, │   │ analytics    │   │ users, costs,  │
│  studio     │   │              │   │ RAG, guardrails│
└─────────────┘   └──────────────┘   └────────────────┘
         │                 │                  │
         └─────────────────┴──────────────────┘
                           │
                    ScholarSync API
                    (tenant-scoped)
```

- **Student** — primary product surface under `apps/web/src/app/(student)/`
- **Teacher** — `apps/web/src/app/teacher/`
- **Admin / ops** — `apps/web/src/app/admin/`

---

## 4. High-level architecture

```
Browser (Next.js 14)
   │  HTTPS + Bearer JWT + Host / x-tenant-id
   ▼
FastAPI (apps/api)
   │  TenantMiddleware → Auth → Routes → Services
   ▼
packages/core  ──────────────────────────────────────────
   │ LangGraph chat graph
   │ RAG (chunk → embed → hybrid retrieve → rerank → generate)
   │ Security / guardrails
   │ Tutor / Problem Solver / Studio services
   ▼
┌────────────┬─────────────┬──────────────┬─────────────┐
│ PostgreSQL │  Pinecone   │ Redis/Celery │ S3/Supabase │
│ (OLTP)     │ (vectors)   │ (cache/jobs) │ (files)     │
└────────────┴─────────────┴──────────────┴─────────────┘
   │
   └─ LLMs: OpenAI / Anthropic / Gemini (+ Cohere rerank)
```

### Design principles (say this in interviews)

1. **Monorepo, clear boundaries** — HTTP in `apps/api`, UI in `apps/web`, domain logic in `packages/core`.
2. **Tenant isolation at every layer** — HTTP host → SQL `tenant_id` → Pinecone namespace → storage path.
3. **Grounded generation** — retrieval + context grounding gates before the model answers.
4. **Defense in depth** — moderation, injection detection, intent gate, PII, academic integrity.
5. **Observable & evaluable** — metrics routes, pipeline traces, LangSmith agent matrix.

---

## 5. Monorepo map

```
NotebookLM/
├── apps/
│   ├── api/                 # FastAPI HTTP layer (routes, middleware)
│   ├── web/                 # Next.js 14 App Router (@scholarsync/web)
│   └── worker/              # Celery worker (optional PDF ingestion)
├── packages/
│   ├── core/                # Domain: RAG, LangGraph, services, DB, prompts, security, IIL
│   └── types/               # Shared Zod/TS types (@scholarsync/types)
├── config/                  # settings.py (SSOT), models.yaml, slo.yaml, NCERT subjects
├── docs/                    # Setup guides, API keys, prompt mirrors
├── scripts/                 # seed_db, upload datasets, workspace switch, start helpers
├── tests/                   # pytest unit / integration / load
├── evals/                   # LangSmith agent × prompt × model bake-off
├── infrastructure/          # terraform/k8s/helm placeholders
├── docker-compose.yml       # postgres, redis, api, worker
├── alembic.ini              # → packages/core/database/migrations
├── requirements.txt         # Python deps
├── package.json             # Turborepo + pnpm root
└── README.md                # this file
```

**Important for Python:** run commands from the **repo root** so imports resolve (`apps.api…`, `packages.core…`, `config…`).

---

## 6. Tech stack

### Backend (Python 3.11+)

| Layer | Choice | Why it matters |
|-------|--------|----------------|
| HTTP | FastAPI 0.109 + Uvicorn | Async APIs, OpenAPI docs, SSE streaming |
| ORM | SQLAlchemy 2.0 + asyncpg | Async Postgres access |
| Migrations | Alembic 1.13 | Schema evolution |
| Orchestration | LangGraph 0.2+ | Stateful chat pipeline (nodes + edges) |
| RAG helpers | LlamaIndex adapters | Ingestion/retrieval adapters |
| Vectors | Pinecone 7+ | Namespace-per-tenant isolation |
| LLMs | OpenAI / Anthropic / Gemini | Multi-provider via task→model mapping |
| Rerank | Cohere 5+ | Improve retrieval precision |
| Queue | Celery + Redis | Optional heavy ingestion off the request path |
| Auth | Platform JWT (HS256); Clerk legacy | Username/password portals + deprecated Clerk JWKS |
| Observability | LangSmith, Prometheus metrics routes | Traces + ops dashboards |

### Frontend (Node 18+, pnpm 8)

| Layer | Choice |
|-------|--------|
| Framework | Next.js 14 App Router |
| Server state | TanStack Query 5 |
| Client context | React Context (Chat, Notebook, Sources, Tutor, etc.) |
| Validation | Zod + shared `@scholarsync/types` |
| Editor / viz | Tiptap (notes), D3 (mind maps), KaTeX (math) |
| HTTP | Axios API client with Bearer token |

### Infrastructure (local)

- PostgreSQL **15**
- Redis **7**
- Docker Compose for `postgres` + `redis` + `api` + `worker`

---

## 7. Request lifecycle (one chat message)

Walk an interviewer through this path:

```
1. Student types a question in notebook UI
2. Next.js calls POST /api/v1/chat/stream
   - Authorization: Bearer <platform JWT>
   - Tenant resolved from Host (or localhost → "default")
3. FastAPI TenantMiddleware attaches tenant_id
4. Auth middleware validates JWT → user + role
5. chat route → ChatService → LangGraphChatPipeline
6. Graph nodes run (moderation → memory → route → retrieve/generate → output mod → cache)
7. Tokens stream back as SSE / chunked response
8. Message persisted in Postgres; optional IIL feedback later
```

**Key files**

- Frontend API: `apps/web/src/lib/api-client.ts`
- Route: `apps/api/routes/chat.py`
- Graph: `packages/core/langgraph/chat_graph.py`
- State schema: `packages/core/langgraph/chat_state.py`

---

## 8. Multi-tenancy

### How tenants are identified

- Production-style host: `lincoln.scholarsync.com` → subdomain `lincoln`
- Localhost: always maps to tenant subdomain **`default`**
- Dev seed (`scripts/seed_db.py`) creates that tenant with a fixed UUID for stable local data

### Isolation layers (must say all three)

| Layer | Mechanism |
|-------|-----------|
| HTTP | `TenantMiddleware` resolves tenant from host / headers |
| Database | Every query filters by `tenant_id` |
| Vectors | Pinecone **namespace** = normalized tenant id |
| Files | Storage paths scoped by tenant |

**NCERT exception:** global NCERT corpus can live in a shared namespace (e.g. `NcertDataGlobal`) while still being access-controlled through tutor APIs and relevance gates.

---

## 9. Authentication & authorization

### Current primary model: Platform JWT

1. User signs in at `/sign-in`
2. `POST /api/v1/auth/login` verifies username/password
3. Server issues JWT signed with `PLATFORM_JWT_SECRET`
4. Browser stores token + sets `platform_session` cookie
5. Next.js middleware protects routes; role `schooladmin` → admin, else student home
6. API calls send `Authorization: Bearer …`

**Key files:** `apps/api/routes/auth.py`, `apps/web/src/lib/platform-auth.ts`, `apps/web/src/middleware.ts`

### Additional portals

| Portal | Purpose | Secrets (env) |
|--------|---------|----------------|
| Admin portal | Ops: users, metrics, guardrails, NCERT global | `ADMIN_PORTAL_*` |
| Teacher portal | Exams / analytics | `TEACHER_PORTAL_*` |

### Legacy

Clerk JWKS verification still exists in settings/middleware for transition, but platform JWT is the active student/admin flow.

---

## 10. Data model (core entities)

High-level ER mental model:

```
Tenant ─┬─ Notebook ─┬─ Source ── SourceQuestion
        │            ├─ Chat ──── Message (+ feedback)
        │            ├─ Note
        │            └─ StudioFeature
        ├─ User
        ├─ ProblemSolverSession ── Steps / SessionChat
        └─ IIL: InteractionLog, Feedback, CurationCandidate, Artifacts

Also: NcertGlobalDocument, NcertCatalogChapter, GuardrailUserBlock, AlertUserSession
```

Models live under `packages/core/database/models/`.  
Migrations: `packages/core/database/migrations/versions/` (Alembic).

---

## 11. Source ingestion pipeline

```
Upload (PDF / text / link)
   → store file (S3 / Supabase Storage)
   → create Source row (status: processing)
   → extract text
   → semantic / structured chunking (chunker + LlamaIndex adapters)
   → embed (OpenAI text-embedding-3-small, typically 1024 dims)
   → upsert vectors into Pinecone namespace(tenant)
   → mark Source ready
```

- Default path: FastAPI `BackgroundTasks`
- Optional path: Celery task `process_source_ingestion` when `ENABLE_CELERY_INGESTION=true`
- Worker: `apps/worker/tasks/pdf_task.py`

**Interview tip:** call out why ingestion is async — PDFs can be large; you don’t want to block the upload HTTP request.

---

## 12. RAG system (deep dive)

### Pipeline stages

```
Query
  → Intent classify / rewrite / (optional) decompose
  → Hybrid retrieve (vector + BM25 fusion)
  → Optional Cohere rerank
  → Context select / dedupe / MMR / early-stop
  → Two-stage grounding + ContextGroundingGate
  → TutorRelevanceGate / SourceRelevanceGate (mode-dependent)
  → Generate (RAG prompt with citations contract)
  → Hallucination / citation enforce / length limit / format
```

### Important modules (`packages/core/rag/`)

| Module | Role |
|--------|------|
| `chunker.py` | Split documents into retrieval units |
| `embedder.py` | Embedding API wrapper |
| `hybrid_retriever.py` / `bm25_fusion.py` | Dense + sparse fusion |
| `rerank/cohere_reranker.py` | Precision boost |
| `context_grounding_gate.py` | Block weak / off-topic context |
| `hallucination_guard.py` | Output fact-checking heuristics |
| `dialog_router.py` | Skip RAG for pure chit-chat |
| `whole_file_map_reduce.py` | Summarize whole documents when needed |
| `contextual_retrieval/` | Document sketch + chunk contextualization |
| `agents/*` | Intent, rewriter, scope narrower, citation enforcer, etc. |

### Why hybrid retrieval?

Vector search alone misses exact keyword matches (formulas, IDs, named theorems). BM25 catches lexical hits. Fusion + rerank balances recall and precision — a classic production RAG pattern.

---

## 13. LangGraph chat orchestration

The chat path is a **state machine**, not a single prompt call.

### Main nodes (simplified)

```
ModerationInput
    → Memory
    → CacheCheck
    → DialogRoute
         ├─ DirectChat ──────────────────────────────┐
         └─ IntentClassify                           │
               ├─ WholeFileMapReduce                 │
               └─ Retrieval → ContextSelector        │
                    → TwoStageGrounding              │
                    → ContextGroundingGate           │
                    → TutorRelevanceGate /           │
                      SourceRelevanceGate            │
                    → Generate ──────────────────────┤
                                                     ▼
                                          ModerationOutput
                                              → Evaluator
                                              → CacheStore
                                              → END
```

**Source of truth:** `packages/core/langgraph/chat_graph.py`

### Why LangGraph?

- Explicit control flow (gates can refuse before generation)
- Shared `ChatGraphState` across nodes
- Easier to instrument (pipeline traces) and evaluate node-by-node
- Caching and early exits without spaghetti `if` trees in one mega-function

---

## 14. Feature deep dives

### 14.1 Notebook RAG chat

- Notebooks hold sources + chats + notes
- Streaming responses for UX
- Citations and relevance gates keep answers tied to uploaded material

### 14.2 Studio

Generates study assets from retrieved context:

| Artifact | Typical use |
|----------|-------------|
| Quiz | Practice MCQs |
| Flashcards | Spaced recall |
| Mind map | Concept hierarchy (D3 visualization) |
| Slide deck | Revision slides |

API: `apps/api/routes/studio.py` + `studio_features.py`  
Service: `packages/core/services/studio_service.py`  
UI: `(student)/studios`, `(student)/assets`

### 14.3 Tutor mode (NCERT)

1. Browse / select chapter from NCERT catalog  
2. **Prepare / bootstrap** notebook context from global NCERT corpus  
3. Chat with **tutor relevance gate** so answers stay on-syllabus  
4. Follow-up question generation for guided study  

API: `apps/api/routes/tutor.py`  
UI: `(student)/tutor`, `tutor-mode`

### 14.4 Problem solver (coaching modes)

Stateful session FSM (service-driven; thin LangGraph facade):

```
created → extracting → dna_ready → mode_selected → responding → follow_up → completed
```

**Modes**

| Mode | Intent |
|------|--------|
| `EXPLAIN_FROM_BASICS` | Teach prerequisites first |
| `HELP_ME_SOLVE_IT` | Guided solving without dumping full answer early |
| `SHOW_MISSING_IDEA` | Reveal the key insight the student is missing |
| `SHOW_BEST_APPROACH` | Show the optimal method |

Flagged by `ENABLE_PROBLEM_SOLVER` / `NEXT_PUBLIC_ENABLE_PROBLEM_SOLVER`.

### 14.5 Notes

Tiptap-based rich notes scoped to notebooks (`/api/v1/notes`).

### 14.6 Admin & teacher portals

- **Admin:** users, documents, guardrails, agents, RAG metrics, cost/tokens, alerts, pipeline traces, NCERT global ingestion, IIL curation, portal settings, roles
- **Teacher:** exams CRUD + analytics

### 14.7 IIL (Interaction Intelligence Layer)

Logs interactions, feedback, curation candidates, and derived knowledge artifacts so the product can improve over time (`packages/core/iil/`). Scheduler starts on API lifespan.

---

## 15. Security & guardrails

Defense layers under `packages/core/security/`:

| Control | What it does |
|---------|----------------|
| OpenAI moderation (in/out) | Block unsafe content; educational heuristics for false positives |
| Prompt injection detector | Pattern + embedding similarity |
| Intent gate | Prefer academic / on-product intents |
| PII detector | Reduce sensitive data leakage |
| Academic integrity / cheating detector | Discourage “do my exam for me” abuse |
| Youth distress / safety filter | Safer responses for minors |
| Syllabus lock (optional) | Constrain answers to allowed curriculum |
| Rate limits + monthly budgets | Cost / abuse control |
| Refusal templates | Consistent, policy-aligned refusals |

Admin UI: `/admin/guardrails`

**Interview framing:** “We treat educational AI as a regulated UX — not just an LLM wrapper. Guardrails sit *inside* the graph before and after generation.”

---

## 16. Frontend architecture

### App Router groups

| Group | Path | Audience |
|-------|------|----------|
| Auth | `(auth)/sign-in`, `sign-up` | Everyone |
| Student | `(student)/home`, `library`, `notes`, `studios`, `tutor`, `problem-solver`, … | Students |
| Notebook | `notebook/[slug]` | Deep work surface |
| Admin | `admin/*` | School / ops admins |
| Teacher | `teacher/*` | Teachers |

### State management pattern

- **TanStack Query** — server data (notebooks, sources, chats, metrics)
- **React Context** — session UX (active notebook, chat stream, tutor/problem-solver UI state)
- **Zustand** is listed in dependencies but the live pattern in `src/` is Query + Context

### Auth UX flow

Login → store JWT → cookie `platform_session=1` → middleware gate → role-based redirect.

---

## 17. Backend API surface

Base: `/api/v1/...` · Docs (dev): `http://localhost:8000/api/docs` · Health: `/health`

| Area | Prefix / file | Responsibility |
|------|---------------|----------------|
| Auth | `/auth` | login, logout, me, profile |
| Chat | `/chat` | stream, history, summarize |
| Sources | `/ingest` | upload, list, delete, extract questions |
| Studio | `/studio` | generate + saved features |
| Notes / Notebooks | `/notes`, `/notebooks` | CRUD |
| Tutor | `/tutor` | catalog, prepare, bootstrap, follow-ups |
| Problem solver | `/problem-solver` | sessions, extract, modes, stream |
| Home | `/home` | summary widgets |
| Metrics / dashboards | `/metrics`, `/dashboards` | cost, latency, RAG quality, IIL |
| Admin | `/admin` | users, NCERT global, curation, portal config |
| Teacher | `/teacher` | teacher portal auth |
| Pipeline traces | `/pipeline-traces` | debug explainability |

Entry: `apps/api/main.py` (middleware: tenant → logging → security headers → CORS).

---

## 18. Workers & async jobs

| Component | Role |
|-----------|------|
| `apps/worker/celery_app.py` | Celery app, Redis broker |
| `tasks/pdf_task.py` | `process_source_ingestion` (active) |
| cleanup / usage aggregation | stubs / TODO |

Toggle: `ENABLE_CELERY_INGESTION` (default `false` → use FastAPI background tasks).  
On Windows use Celery `--pool=solo` or `--pool=threads`.

---

## 19. Config, env, and feature flags

**Single source of truth:** `config/settings.py` (hundreds of flags for RAG, tutor, guardrails, Celery, IIL, budgets).

### Env files (split on purpose)

| File | Consumer |
|------|----------|
| `/.env` | FastAPI, Alembic, scripts, Docker |
| `apps/web/.env.local` | Next.js (`NEXT_PUBLIC_*`, portal keys as needed) |

### Categories you should memorize

- **Core:** `DATABASE_URL`, `ENVIRONMENT`, `CORS_ORIGINS`
- **Auth:** `PLATFORM_JWT_*`, bootstrap admin, admin/teacher portal secrets
- **AI:** `OPENAI_API_KEY`, `GEMINI_API_KEY`, `COHERE_API_KEY`, `PINECONE_*`
- **Storage:** `AWS_*` / `SUPABASE_*`
- **Queue:** `REDIS_URL`, `ENABLE_CELERY_INGESTION`
- **Product flags:** `ENABLE_PROBLEM_SOLVER`, `USE_LANGGRAPH_CHAT`, `LANGSMITH_*`
- **Web:** `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_ENABLE_PROBLEM_SOLVER`

Full key guide: [`docs/API_KEYS_EXPLAINED.md`](docs/API_KEYS_EXPLAINED.md)

> Tip: if `DATABASE_URL` password has `@ # $ :`, URL-encode them or auth will fail mysteriously.

---

## 20. Eval / quality system (LangSmith)

ScholarSync treats prompts as **versioned products**.

- Datasets under `evals/datasets/prompt_tiered/`
- Per-agent evaluators in `evals/datasets/final_Evalutors/`
- Matrix runner: `evals/agent_eval/run_matrix.py` (`--step`, `--all`, `--agent`, `--status`)
- Prompt versions: `evals/agent_eval/prompt_versions/{agent}/v1|v2|v3.json`
- Models matrix: `evals/agent_eval/agent_models.json`
- Free-tier trace budget tracking via local ledger (`trace_ledger.json`)

**Why interviewers care:** you can explain *how* you know which prompt/model combo ships — not vibes, metrics.

Soft CI gate: `.github/workflows/eval-regression.yml`

---

## 21. Testing strategy

```bash
pytest                     # default suite
pytest tests/unit/         # fast, no live services
INTEGRATION_TESTS=1 pytest tests/integration/
pytest -m retrieval        # marker-based
```

Markers include: `integration`, `ingestion`, `retrieval`, `notebook_mode`, `studio`, `guardrails`, `slow`, `load`.

Load: Locust files under `tests/load/`.

---

## 22. Local setup & run

### Prerequisites

- Node 18+, pnpm 8+
- Python 3.11+
- PostgreSQL 15+, Redis (or Docker Compose)
- API keys: OpenAI (and/or Gemini/Anthropic), Pinecone, storage, platform JWT secrets

### Install

```bash
# Node
pnpm install

# Python (from repo root)
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

# Env
cp .env.example .env
# create apps/web/.env.local with NEXT_PUBLIC_API_URL=http://localhost:8000
# (+ platform / Clerk keys as needed)

# DB
alembic upgrade head
python scripts/seed_db.py
```

### Run (two terminals)

```bash
# API — http://localhost:8000  (docs: /api/docs)
python -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# Web — http://localhost:3000
pnpm dev
```

### Docker alternative

```bash
docker compose up
# or: docker compose up postgres redis api
```

### Handy Makefile / pnpm

```bash
make migrate
make test
make lint
pnpm build
pnpm type-check
pnpm --filter @scholarsync/types build
```

### Supabase notes

Preferred: Alembic migrations (RLS enabled; `anon`/`authenticated` revoked — **backend-only** DB access).  
Quick SQL alternative: `scripts/supabase_schema.sql` then `alembic stamp head` + seed.

Under classroom SSE load, prefer Supabase **transaction pooler `:6543`**.

### Dev tenant seed

| Field | Value |
|-------|--------|
| subdomain | `default` |
| name | Development School |
| id | `eeff7c1c-fe22-4573-ad93-a36f19ad4dc5` |

Idempotent — safe to re-run.

### ChunkLoadError in Next dev

Usually stale `.next` or two `next` processes. Stop servers, clear `apps/web/.next`, run `pnpm dev` once (or `pnpm dev:web:clean` if available).

---

## 23. Deployment mental model

Local Compose ≈ production shape:

| Service | Responsibility |
|---------|----------------|
| `api` | FastAPI / Uvicorn |
| `worker` | Celery ingestion |
| `postgres` | System of record |
| `redis` | Broker + caches |
| Managed Pinecone | Vectors |
| S3 / Supabase Storage | Objects |
| Next.js host (Vercel or Node) | UI |

`infrastructure/{terraform,kubernetes,helm}` are placeholders for future IaC.

---

## 24. Interview talking points & common questions

### 60-second architecture answer

> “ScholarSync is a monorepo. Next.js talks to FastAPI. Every request is tenant-scoped. Uploaded sources are chunked and embedded into Pinecone namespaces. Chat runs through a LangGraph state machine with moderation, retrieval, grounding gates, generation, and output checks. Postgres stores notebooks/chats; Redis backs optional Celery ingestion and caches. We also have tutor, problem-solver, and studio features, plus LangSmith evals for prompt quality.”

### “Why not just call the LLM with the PDF?”

Context windows, cost, latency, and hallucination risk. Chunking + hybrid retrieval + grounding gates scale better and keep answers attributable.

### “How do you prevent cross-school data leaks?”

Tenant on the HTTP edge, `tenant_id` on every row, Pinecone namespace isolation, storage path scoping — never “trust the client’s notebook id alone.”

### “How do you reduce hallucinations?”

Hybrid retrieval, rerank, context grounding gate, citation enforcement, output moderation, optional hallucination guard, and eval harnesses.

### “What’s hard about educational AI?”

Curriculum fidelity, minor safety, academic integrity, multi-tenant ops, and measurable quality — not just demo chat.

### “Walk me through adding a new Studio artifact.”

Prompt template → service generation path → API route → Zod/types → UI page → evaluator dataset entry (if quality-gated).

### Strong phrases to use

- “Grounded generation with explicit refusal paths”
- “Namespace-per-tenant vector isolation”
- “Graph orchestration instead of a prompt spaghetti”
- “Eval-driven prompt iteration with LangSmith”
- “Backend-only DB access with RLS as a safety net”

---

## 25. Glossary

| Term | Meaning |
|------|---------|
| RAG | Retrieval-Augmented Generation |
| Hybrid retrieval | Vector + BM25 fused search |
| Grounding gate | Block answers when retrieved context is weak/irrelevant |
| Namespace | Pinecone partition (here: per tenant) |
| LangGraph | Stateful agent/workflow library |
| IIL | Interaction Intelligence Layer (feedback → curation) |
| Studio | Generative study-asset factory |
| NCERT | Indian national curriculum textbooks used in tutor mode |
| SSE | Server-Sent Events (streaming responses) |

---

## 26. Further docs

- [`docs/API_KEYS_EXPLAINED.md`](docs/API_KEYS_EXPLAINED.md) — env vars
- [`docs/PYTHON_SETUP_GUIDE.md`](docs/PYTHON_SETUP_GUIDE.md) — Python troubleshooting
- [`docs/used_prompts/README.md`](docs/used_prompts/README.md) — prompt template mirror
- [`CLAUDE.md`](CLAUDE.md) — engineering guide + LangSmith eval SOP
- Product/API specs in repo root / `docs/` (PRD, API specification, etc.)

---

## 27. License

Private — All Rights Reserved.
