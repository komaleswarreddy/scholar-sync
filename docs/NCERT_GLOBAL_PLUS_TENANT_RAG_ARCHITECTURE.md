# NCERT Global + Tenant RAG Architecture (Production Blueprint)

This document defines a production-grade architecture for your multi-tenant RAG system with:

- a **shared global NCERT knowledge base** (Classes 6-10, all subjects),
- **tenant-private uploads**,
- and **combined retrieval** for final answer generation.

---

## 1) Pinecone Architecture: Indexes vs Namespaces vs Metadata

### Recommended model for your project

Use **one Pinecone index per embedding model + dimension**, and split data by namespace:

- `global_ncert` namespace: shared NCERT vectors for all tenants
- `tenant_<tenant_id>` namespace: private user/tenant vectors

Why this is best for your case:

- Single index keeps operations simple and cheaper than many indexes.
- Namespaces give hard logical separation and clean query controls.
- You can query global + tenant in parallel, then merge.

### Metadata schema (critical)

Store rich metadata on every chunk:

- `kb_type`: `global` | `tenant`
- `source_id`: internal source UUID
- `source_title`
- `tenant_id` (for tenant namespace also keep metadata for auditing)
- `board`: `ncert`
- `class`: `6|7|8|9|10`
- `subject`: `math|science|history|...`
- `chapter_no`
- `chapter_title`
- `topic`
- `language`
- `chunk_index`
- `page_start`, `page_end`
- `text` (shortened if needed)
- `version` (for re-ingest rollouts)

### ID strategy

Use deterministic vector IDs:

- Global: `ncert_{class}_{subject}_{chapter}_{source_id}_chunk_{i}`
- Tenant: `{source_id}_chunk_{i}` (or `tenant_{tenant_id}_{source_id}_chunk_{i}`)

Deterministic IDs make re-index and delete reliable.

---

## 2) Ingestion Strategy for NCERT (Very Important)

### A. Pre-ingestion normalization

For each NCERT book:

1. Extract text with page boundaries.
2. Remove noisy headers/footers/page numbers.
3. Preserve structural markers:
   - class, subject, chapter titles, section headings, definitions, examples, exercises.
4. Add document manifest entry:
   - checksum, source version, ingestion timestamp.

### B. Chunking strategy (NCERT-specific)

Use **hierarchical chunking**, not plain fixed windows:

1. **Primary split by chapter/section headings**.
2. Inside section, semantic chunks with target:
   - 500-900 tokens per chunk,
   - 10-15% overlap.
3. For formulas/definitions/theorems:
   - keep them intact in a single chunk if possible.
4. Add **question-answer anchor chunks** for exercise/problem blocks.

Why:

- NCERT has structured pedagogy (concept -> example -> exercise). Heading-aware chunking gives much better retrieval than naive split-by-length.

### C. Dual embeddings (optional but high quality)

For global NCERT at scale:

- Primary dense embedding: OpenAI `text-embedding-3-small` (or your chosen model).
- Optional sparse/lexical signal for exact terms (names, years, terms in SST/Biology).

### D. Quality gates before publish

Promote a book to `INDEXED` only if:

- min chunk count threshold is met,
- random sample queries return expected chapters,
- no extraction-empty pages across major sections.

Maintain statuses:

- `PROCESSING` -> `INDEXING` -> `INDEXED` -> `ERROR`.

---

## 3) Retrieval: Clean Merge of Global + Tenant (Most Important)

### Query plan

For every user query:

1. Intent classify (factual / explanation / compare / solve / summary).
2. Query rewrite variants (1-3 max).
3. Run retrieval in parallel:
   - global namespace (`global_ncert`) with filters by class/subject when inferred,
   - tenant namespace (`tenant_<tenant_id>`) with selected sources filter.
4. Rerank combined candidate pool.
5. Select final context budget for LLM.

### Candidate budget (starting point)

- Global fetch: top 24-40
- Tenant fetch: top 16-24
- Merge pool: 40-60
- Final context chunks to LLM: 10-16 (token-budget aware)

### Merge policy (recommended)

Use weighted blending before rerank:

- `tenant_boost`: +0.08 to +0.18 score (user content preference)
- `global_boost`: +0.00 (baseline)

Then run final reranker (Cohere/OpenAI rerank style).  
This ensures user notes win when equally relevant, but global NCERT still fills missing facts.

### Conflict policy

If tenant chunk conflicts with NCERT fact:

- If user asks from their own notes, prefer tenant and mark as "from your uploaded material".
- Else for factual textbook questions, prioritize NCERT evidence.

---

## 4) Low Latency + High Accuracy at Scale

### Performance controls

- Parallel retrieval global+tenant.
- Retrieval cache for rewrite/rerank.
- Answer cache for repeated exact queries + same sources.
- Short-lived DB sessions (avoid holding DB connection during full SSE stream).

### Accuracy controls

- Metadata-aware query expansion (author/date/first/when/who variants).
- Fallback guardrail: if score-threshold filtering empties context, keep top scored chunks.
- Min chunk floor for LLM context.

### Observability

Track per request:

- namespace hit mix (`global_count`, `tenant_count`)
- rerank score distribution
- final selected chunk sources
- not-found rate by subject/class
- latency p50/p95 for each retrieval stage

---

## 5) Deletion & Data Lifecycle (Production Safety)

For tenant source delete:

1. Remove citations in chat history referencing that `source_id`.
2. Delete vectors in tenant namespace by metadata filter (`source_id`).
3. Delete object storage file.
4. Delete DB source row.
5. Write audit log.

For global NCERT updates:

- versioned ingestion (`version` metadata),
- blue/green cutover:
  - ingest new version,
  - validate retrieval,
  - switch active version flag,
  - retire old vectors.

---

## 6) Concrete Recommendation for Your Current Codebase

Given your stack (FastAPI + Pinecone + LlamaIndex adapters + retrieval agents):

1. Keep one index, introduce two namespace classes:
   - `global_ncert`
   - `tenant_<tenant_id>`
2. Extend ingestion pipeline with NCERT metadata (`class`, `subject`, `chapter_*`).
3. Add global retrieval adapter call in retriever and merge with tenant results.
4. Keep current rerank/context selector but enforce:
   - factual variants,
   - non-empty fallback chunks,
   - tenant-priority merge bias.
5. Keep strict source ownership checks for tenant data, but global namespace has no tenant ownership check.

---

## 7) Example End-to-End Flow

Query: `Who performed the first kidney transplantation, and when?`

1. Rewriter emits:
   - original query
   - factual variants (`history timeline key people dates`)
2. Retrieve:
   - Global NCERT biology/history chunks
   - Tenant-selected source chunks
3. Merge + rerank:
   - tenant chunks slightly boosted
4. Context select:
   - top 12 chunks with at least 6 minimum fallback
5. LLM answers using both pools; citations map source origin (`global`/`tenant`).

---

## 8) Final Decision Summary

- **Indexes**: one per embedding model/dimension.
- **Namespaces**: `global_ncert` + `tenant_<tenant_id>`.
- **Metadata filters**: class/subject/chapter/source.
- **Chunking**: heading-aware + semantic + overlap; preserve educational structure.
- **Retrieval merge**: parallel global+tenant, weighted blend, rerank, token-budget context select.
- **Operations**: versioned ingestion, deterministic IDs, strong delete workflow, full observability.

