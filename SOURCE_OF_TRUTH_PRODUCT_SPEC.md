# ScholarSync — Source of Truth Product Spec (V1)

**Doc status**: Living spec (source of truth)  
**Scope**: **V1** target (may exceed current code in places; deviations are called out)  
**Primary users**: Mixed (students, teachers, school admins, internal ops)  
**Multi-tenancy**: Required in production via subdomain (e.g. `tenant.scholarsync.com`); localhost maps to `default`  
**Safety posture**: **Hybrid** (Tutor mode may allow general knowledge; dashboard/workspace chat is source-grounded by default)  
**NFR coverage**: Security/Compliance, Privacy/Retention, Latency, Scale, Reliability, Cost, Observability, Accessibility (**all in-scope**)  

---

## 1) Executive summary (non-technical)

ScholarSync is an AI notebook platform for educational institutions. It enables users to upload or connect learning materials (“sources”), chat with those materials using retrieval-augmented generation (RAG) with citations, and generate study artifacts via “Studio” tools (quizzes, flashcards, reports, etc.). The product is tenant-aware (school/org subdomains) and integrates authentication via Clerk.

**Outcomes we optimize for**
- Faster comprehension and study workflows from school-approved materials
- Reduced teacher prep time via structured generation (quizzes/handouts/reports)
- Safer, more controllable AI use in education (guardrails, source-grounding, tenant isolation)

---

## 2) Goals, non-goals, and assumptions

### 2.1 Goals
- **G1**: Provide a reliable, source-grounded chat experience over uploaded content for each tenant.
- **G2**: Provide a “Tutor mode” experience for a curated global corpus (NCERT), with guardrails and relevance gating.
- **G3**: Provide Studio generation tools that create classroom/study outputs from sources (and optionally from conversation context).
- **G4**: Make tenant isolation and auth rules first-class and testable.
- **G5**: Establish explicit non-functional requirements and operational guardrails (cost, safety, observability).

### 2.2 Non-goals (V1)
- Full LMS replacement (gradebook, assignments, submissions)
- Real-time classroom collaboration (multi-user live editing)
- Offline-first mobile experience
- Full content licensing/DRM enforcement (beyond access control + storage boundaries)

### 2.3 Assumptions (explicit)
- **A1**: Database access is performed **only** through the FastAPI backend (Supabase PostgREST is hardened; RLS enabled + privileges revoked).
- **A2**: Tenant isolation is required across DB rows, vector namespaces, and storage paths.
- **A3**: The platform may operate in a “pilot” footprint (single-school) in V1, but must keep architecture compatible with multi-tenant scale-up.

---

## 3) Personas and roles (non-technical + functional)

### 3.1 Personas (canonical)
- **Student**: Studies from uploaded school materials, asks questions, generates study aids.
- **Teacher**: Uploads/curates sources, generates quizzes/handouts, uses tutor mode for explanations.
- **School Admin**: Manages tenant configuration, policies, and usage oversight.
- **Platform Admin / Ops** (internal): Manages global corpora (e.g., NCERT), monitors cost/latency and guardrails.

### 3.2 Roles & permission model (detailed, V1 target)
V1 must formalize roles. Code currently syncs a local user row with a default role, but feature gating may be partial.

**Roles**
- **Student**
- **Teacher**
- **SchoolAdmin**
- **PlatformAdmin** (internal)

**Capabilities (high-level)**
- **Student**: chat, notes, studio generation (within policies), manage own sources (if allowed by tenant).
- **Teacher**: all student capabilities + upload/curate shared sources + export/share outputs (policy-dependent).
- **SchoolAdmin**: tenant configuration, retention policies, usage dashboards, user/role management.
- **PlatformAdmin**: global corpus ingestion (NCERT), platform-wide monitoring and feature flags.

**Open questions**
- Do teachers manage “shared sources” for a class vs personal sources? (see §12)
- What is the admin UX surface in the web app vs API-only in V1?

---

## 4) Tenant model (functional + technical)

### 4.1 Tenant identity
- Production tenant is derived from **subdomain** of host.
- Local development uses `default`.

### 4.2 Tenant isolation requirements
- **DB**: every tenant-owned entity must include `tenant_id` and be filtered by it.
- **Vectors**: tenant data must be isolated by namespace (or equivalent isolation primitive).
- **Storage**: object keys must be tenant-scoped (prefixes / buckets / policies).

### 4.3 Tenant propagation (current behavior)
- Web middleware injects `x-tenant-id` and `tenantId` cookie.
- API middleware derives tenant from host and sets `request.state.tenant_id`.

**Decision (spec)**: **Backend is the authority** for tenant resolution; frontend header injection is helpful but not relied upon for security.

---

## 5) Core concepts / glossary

- **Source**: An uploaded or connected document (PDF/text). Has ingestion status.
- **Chunk**: A segment of a source used for retrieval and embedding.
- **Workspace**: A user’s working area (Dashboard in UI), containing sources, chats, notes, and outputs.
- **Chat**: A conversation thread with messages + citations and optional feedback.
- **Studio**: Generation tools producing structured outputs from sources and/or chat context.
- **Tutor mode**: A guided learning mode using a curated global corpus (NCERT).
- **Pipeline trace**: A debug artifact capturing retrieval + generation steps for inspection.

---

## 6) Functional spec (what the product does)

### 6.1 Authentication & session management
**User stories**
- As a user, I can sign in and access protected areas.
- As a tenant, my users cannot access another tenant’s data.

**Requirements**
- **FR-AUTH-1**: Protected routes require authentication (Clerk).
- **FR-AUTH-2**: API requests require bearer token for non-public endpoints.
- **FR-AUTH-3**: User identity must be consistent between web and API (Clerk `sub` as canonical user id).

**Notes**
- In development, some tenant-only endpoints may allow unauthenticated access for dashboards/metrics.

### 6.2 Source upload & ingestion
**User stories**
- As a user, I can upload PDFs/text and see ingestion progress.
- As a user, I can delete a source and it is removed from my tenant scope.

**Requirements**
- **FR-SRC-1**: Upload PDF/text → create Source row → enqueue ingestion (background).
- **FR-SRC-2**: Ingestion extracts text, chunks, creates embeddings, indexes into vector store.
- **FR-SRC-3**: Source has lifecycle statuses (e.g., pending/processing/ready/error).
- **FR-SRC-4**: Errors must be visible to user and recorded for debugging.

### 6.3 RAG chat (dashboard/workspace)
**User stories**
- As a user, I can ask questions about my uploaded sources and receive answers with citations.
- As a user, I can continue a conversation; the system uses prior context responsibly.

**Requirements**
- **FR-CHAT-1**: Streaming chat responses (SSE) for responsive UX.
- **FR-CHAT-2**: Retrieval is scoped to the tenant + user-selected sources (when provided).
- **FR-CHAT-3**: Persist chats and messages; allow list/get/update/delete.
- **FR-CHAT-4**: Store citations as structured metadata per message.
- **FR-CHAT-5**: Support feedback on messages (thumbs up/down, etc.).

**Safety/grounding**
- **FR-CHAT-6**: When sources are selected, the system should refuse or constrain answers that are not supported by retrieved context (strict grounding).
- **FR-CHAT-7**: Global knowledge fallback (answer without sources) must be policy-controlled (default off for source-selected chat).

### 6.4 Tutor mode (NCERT global library)
**User stories**
- As a student, I can ask questions within curriculum scope and get guided explanations.
- As a teacher, I can use Tutor mode as a concept explainer.

**Requirements**
- **FR-TUTOR-1**: Provide curriculum filters (class/subject/chapter) and retrieval from a global corpus.
- **FR-TUTOR-2**: Enforce relevance gating (avoid answering from unrelated chunks).
- **FR-TUTOR-3**: Hybrid behavior allowed: if not enough relevant context, optionally answer generally **only if policy allows** (see §10).

### 6.5 Studio generation (quiz/flashcards/mindmap/report/slide deck/infographic)
**User stories**
- As a user, I can generate a quiz/flashcards/report from my sources.
- As a user, I can tailor output (tone, focus, format).

**Requirements**
- **FR-STUDIO-1**: Provide a single “generate” API with task type + parameters.
- **FR-STUDIO-2**: Retrieval strategy differs by task (multi-query, wider context for infographic).
- **FR-STUDIO-3**: Support hybrid context (sources + chat transcript) for some tools.
- **FR-STUDIO-4**: Studio outputs must be reproducible/debuggable via traces (inputs, retrieval summary, model ids, cost where possible).

### 6.6 Notes
**User stories**
- As a user, I can create/edit/delete notes tied to my study workflow.

**Requirements**
- **FR-NOTES-1**: CRUD notes; notes are tenant-scoped and user-scoped.
- **FR-NOTES-2**: Notes may reference sources (optional) for traceability.

### 6.7 Admin & analytics
**User stories**
- As a school admin, I can see usage/cost and set policies.
- As platform ops, I can manage global corpora ingestion and monitor system health.

**Requirements**
- **FR-ADMIN-1**: Provide metrics dashboards (tokens, cost, latency, RAG quality).
- **FR-ADMIN-2**: Provide pipeline trace inspection for debugging.
- **FR-ADMIN-3**: Provide global corpus ingestion endpoints for NCERT and run history.

---

## 7) Non-functional requirements (NFRs) — all in-scope

This section is intentionally explicit. Numeric targets are **TBD** unless you set them now; V1 should still implement measurement and guardrails.

### 7.1 Security & compliance
**Requirements**
- **NFR-SEC-1 (Auth)**: All protected UI routes require auth; API requires JWT bearer token; production verifies signatures and issuer/audience.
- **NFR-SEC-2 (Tenant isolation)**: Tenant scoping enforced server-side for all tenant-owned data.
- **NFR-SEC-3 (Least privilege)**: DB roles `anon`/`authenticated` must not have direct table privileges for app tables (backend-only pattern).
- **NFR-SEC-4 (Auditability)**: Provide audit log events for key actions (login, upload/delete source, generation, admin changes). **TBD**: storage location and retention.
- **NFR-SEC-5 (Encryption)**: Encrypt in transit (TLS). Encrypt at rest where supported (DB/storage). **TBD**: key management approach.
- **NFR-SEC-6 (FERPA-style handling)**: Student data access is role-limited; exports/deletions available; minimize PII exposure in prompts/logs. **TBD**: formal policy and DPA language.

### 7.2 Privacy & data retention
**Decision**: Default retention is **by contract** (tenant-configurable).

**Requirements**
- **NFR-PRIV-1**: Define per-tenant retention windows for sources, chats, notes, and generated outputs.
- **NFR-PRIV-2**: Deletion must propagate to storage and vector indexes (eventual consistency allowed; must be observable).
- **NFR-PRIV-3**: Provide user/tenant export (data portability). **TBD**: format (JSON/CSV), scope, and admin UI.
- **NFR-PRIV-4**: Logging must avoid storing raw sensitive content by default; use redaction and snippet limits.

### 7.3 Latency (UX performance)
**Targets (TBD, pick for pilot)**
- **Chat**: time-to-first-token \(TTFT\) ≤ **TBD** seconds (p50/p95); time-to-complete ≤ **TBD** seconds.
- **Upload ingestion**: “ready” within **TBD** minutes for a **TBD**-page PDF (p50/p95).
- **Studio generation**: completion within **TBD** seconds/minutes depending on task class.

**Requirements**
- Measure p50/p95/p99 at API layer.
- Degrade gracefully when retrieval is slow (stream status events; show progress).

### 7.4 Scale
Because V1 is a single-school pilot, scale targets can be modest but must be explicitly enumerated.

**Targets (TBD)**
- Tenants: **1** (pilot) but design supports many.
- Active users: **TBD** daily active, **TBD** concurrent.
- Sources: **TBD** documents, **TBD** total pages.
- Vector index: **TBD** total chunks and growth rate.

**Requirements**
- Concurrency caps for ingestion and retrieval.
- Backpressure when rate limits trigger; user-visible retry.

### 7.5 Reliability / uptime
**Decision**: No formal SLA yet (“best effort”), but we still define reliability behaviors.

**Requirements**
- **NFR-REL-1**: Graceful degradation on DB pool timeouts (safe empty responses for list endpoints where appropriate).
- **NFR-REL-2**: Retries with bounded exponential backoff for external calls (LLM, Pinecone, storage).
- **NFR-REL-3**: Explicit error categories + user-facing messages (not raw tracebacks).

### 7.6 Cost controls
**Requirements**
- **NFR-COST-1**: Track token usage and per-request cost estimates (by feature).
- **NFR-COST-2**: Rate limits per user/tenant (requests/minute) with configurable thresholds.
- **NFR-COST-3**: Cache answers where safe and policy-allowed; bypass cache for strict gating scenarios.
- **NFR-COST-4**: Per-tenant budgets and alerts. **TBD**: budget enforcement mode (soft/hard).

### 7.7 Observability
**Requirements**
- **NFR-OBS-1**: Structured logs with correlation id / trace id.
- **NFR-OBS-2**: Metrics dashboards: latency, errors, tokens, cost, retrieval quality.
- **NFR-OBS-3**: Pipeline traces retained for debugging with snippet limits and PII safeguards.
- **NFR-OBS-4**: Alerting rules (LLM failures, Pinecone errors, ingestion failures, cost spikes). **TBD**: paging vs email vs dashboard.

### 7.8 Accessibility (WCAG)
**Targets (TBD)**
- WCAG level: **AA** recommended for education.

**Requirements**
- Keyboard navigation for core flows (upload, chat, studio).
- Screen-reader support for chat transcript and generated outputs.
- Color contrast compliance; focus states; reduced motion.

---

## 8) Technical architecture (how it works)

### 8.1 High-level architecture
- **Frontend**: Next.js (App Router), Clerk auth, API calls to FastAPI.
- **Backend**: FastAPI + async SQLAlchemy, Alembic migrations, RAG pipeline using LangGraph/LlamaIndex adapters.
- **Data stores**: Postgres (system of record), Pinecone (vectors), object storage (S3/Supabase), Redis (caches).

### 8.2 Key backend modules (conceptual)
- **Tenant/Auth middleware**: resolves tenant and user and injects into request state.
- **Ingestion pipeline**: upload → extract → chunk → contextualize (optional) → embed → index.
- **Retrieval + chat pipeline**: route intent → retrieve → pack context → apply guardrails → stream response.
- **Studio pipeline**: task-specific retrieval + prompt templates + output formatting + trace recording.

### 8.3 Data model (canonical entities)
V1 canonical entities include:
- `Tenant`
- `User` (local role mirror)
- `Source`
- `Chat`, `Message`
- `Note`
- Global corpus entities for NCERT ingestion runs

### 8.4 API surface (V1)
V1 includes:
- Chat streaming + chat history endpoints
- Ingest upload/list/delete
- Studio generate
- Notes CRUD
- Metrics/dashboards/alerts
- Admin endpoints (including NCERT global ingestion)
- Pipeline trace inspection

---

## 9) Functional-to-technical traceability (requirements → evidence)

This spec is grounded in current implementation and configuration. Canonical references include:
- Web tenant/auth middleware: `apps/web/src/middleware.ts`
- API app + routers: `apps/api/main.py`
- Tenant middleware: `apps/api/middleware/tenant.py`
- Settings and guardrails: `config/settings.py`
- Docker topology: `docker-compose.yml`

---

## 10) Policy decisions (explicit toggles)

### 10.1 Grounding policy (default)
- Dashboard/workspace chat: **strictly grounded** when sources selected; policy-controlled fallback.
- Tutor mode: **hybrid** allowed (can answer generally when corpus retrieval is insufficient), with relevance gates.

### 10.2 Rate limiting policy
- Enforced per user; tenant-level overrides allowed. Defaults must be safe for pilot.

### 10.3 Data retention policy
- **By contract** per tenant. Implementation must support configuration + enforcement + deletion workflows.

---

## 11) Testability and acceptance criteria (V1)

### 11.1 Functional acceptance
- Upload PDF → ingestion completes → appears in sources list → chat can cite it.
- Chat streaming TTFT measured; citations present and structurally valid.
- Studio generation returns output for each supported task type.
- Tutor mode filters work and relevance gating prevents off-topic answers.

### 11.2 NFR acceptance (measurement-based)
- Logging/metrics available for: latency, error rates, tokens, cost, ingestion outcomes.
- Rate limiting can be triggered and produces correct user-visible error.
- Tenant isolation tests: cannot access cross-tenant sources/chats/notes (API and retrieval).

---

## 12) Open questions (to resolve to make this truly “source of truth”)

Answering these will let us replace TBDs with concrete targets and finalize role/permission semantics.

1) **RBAC**: Which routes/features are restricted to Teacher vs Student vs SchoolAdmin vs PlatformAdmin in V1?
2) **Shared vs personal sources**: Can teachers publish sources to a class/tenant library, or are all sources user-private?
3) **Studio outputs storage**: Should generated artifacts be persisted server-side (DB/storage) vs client-side only?
4) **Audit logs**: What events are required for the pilot? Where do we store them and for how long?
5) **Exact latency targets**: TTFT, chat completion, ingestion time, studio generation (p50/p95).
6) **Data retention defaults**: For the pilot tenant, what are the default windows for sources/chats/notes?
7) **Accessibility target**: Is WCAG **AA** required for V1 pilot?
8) **Export**: Do you need export for tenant admins in V1, or can it be roadmap?

---

## 13) Change log

- 2026-05-27: Initial draft created from codebase + alignment answers.

