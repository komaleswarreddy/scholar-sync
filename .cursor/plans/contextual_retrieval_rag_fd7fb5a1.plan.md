---
name: Contextual Retrieval RAG
overview: Replace the current Traditional RAG chunk indexing approach with Contextual Retrieval (OpenAI instead of Claude) by enriching each chunk at ingestion time with compact contextual metadata, embedding context+chunk, and enhancing keyword/hybrid retrieval to use the added context—while keeping citations clean by storing context separately from raw chunk text. Includes production-ready rollout controls, caching, and observability.
todos:
  - id: todo-contextualizer
    content: Add OpenAI-based chunk contextualizer + prompt template (target <=50 tokens by default) and model routing (new task_type).
    status: pending
  - id: todo-ingestion
    content: "Integrate contextual embeddings into `packages/core/rag/llama_adapters/ingestion.py`: store `metadata.text` raw; add contextual metadata (chunk_context + chunk_summary + chunk_type + section_title + concept_hint); embed concatenation of these fields + raw chunk."
    status: pending
  - id: todo-cache
    content: Extend `ContextCache` to persist and reuse contextual metadata per chunk on cache hits (context/summary/type/section/concept_hint).
    status: pending
  - id: todo-hybrid
    content: Update `packages/core/rag/hybrid_retriever.py` to include contextual metadata in keyword scoring text while keeping citations unchanged.
    status: pending
  - id: todo-query-decomposition
    content: Add optional query-decomposition step (primary_concept + sub_queries) integrated into retrieval_agents, guarded by feature flag.
    status: pending
  - id: todo-retrieval-weighting
    content: Add optional context-aware weighting step (boost intent/type matches, penalize redundancy) applied after reranker, guarded by feature flag.
    status: pending
  - id: todo-tests-observability
    content: Add targeted tests + verification script updates; add trace spans and usage tags for ingestion contextualization and retrieval improvements.
    status: pending
isProject: false
---

## Goal

Implement **Contextual Retrieval** as described in `[docs/contextual_retrieval_guide_markdown_conversion.md](docs/contextual_retrieval_guide_markdown_conversion.md)`: for each chunk, generate a short context that situates it within the **whole document**, prepend that context before embedding, and combine **semantic + lexical** retrieval signals.

Additionally (from your screenshots), enrich chunks during ingestion to improve semantic recall and indirect-question handling:

- `chunk_summary` (keep **<= 50 tokens** by default)
- `chunk_type`
- `section_title`
- `concept_hint`

Optional follow-on improvements (feature-flagged):

- Query decomposition at query time: `primary_concept`, `sub_queries[]`
- Context-aware retrieval weighting: boost chunks matching intent/type; penalize redundancy (plug after reranker)

## Decisions (from you)

- **Backfill**: **New uploads only** (no reindex of already-indexed Pinecone vectors).
- **Storage**: **Keep raw chunk in `metadata.text`** for clean citations; store contextual metadata separately (e.g. `metadata.chunk_context`, `metadata.chunk_summary`, etc.) and embed a concatenation of contextual fields + raw chunk.

## Current pipeline touchpoints (where changes go)

- **Ingestion + indexing (primary change)**
  - `[packages/core/services/source_service.py](packages/core/services/source_service.py)`: calls LlamaIndex ingestion adapter.
  - `[packages/core/rag/llama_adapters/ingestion.py](packages/core/rag/llama_adapters/ingestion.py)`: builds `TextNode`s and writes to Pinecone (this is the best insertion point).
- **Chat retrieval (secondary change, to leverage lexical context)**
  - `[packages/core/rag/retriever.py](packages/core/rag/retriever.py)`: uses `HybridRetriever` and optional Cohere rerank.
  - `[packages/core/rag/hybrid_retriever.py](packages/core/rag/hybrid_retriever.py)`: BM25-like scoring currently uses `metadata.text` only.

## Design

### A) Context generation module (OpenAI, Claude-style prompt; production-ready)

Create a small “contextualizer” service that:

- Accepts `whole_document_text` and `chunk_text`.
- Produces compact context fields (default targets for production cost/latency):
  - `chunk_context`: **<= 50 tokens** (configurable)
  - `chunk_summary`: **<= 50 tokens** (configurable)
  - `chunk_type`: small label (definition/procedure/example/table/figure/argument/etc.)
  - `section_title`: best-effort heading/section name
  - `concept_hint`: 3–10 keywords/entities/identifiers likely to be queried
- Uses a prompt equivalent to the guide (adapted to OpenAI):
  - Input: whole document + “Here is the chunk…” + instruction
  - Output: **only a succinct JSON object** containing the fields above (production-friendly parsing)
- Adds guardrails:
  - Hard cap output length (token/char based)
  - Retry once if empty
  - Concurrency limit + backoff (ingestion background tasks can run in parallel across users)
  - Safe fallbacks: if contextualization fails, proceed with raw chunk embedding (do not fail the whole ingestion)

Files to add/use:

- Add: `packages/core/rag/contextual_retrieval/contextualizer.py` (new)
- Add: a prompt template under `packages/core/prompts/templates/rag/` or `studio/` (new) to keep prompts consistent with the repo’s `load_prompt` pattern.
- Use model routing in `[packages/core/llm/factory.py](packages/core/llm/factory.py)` (new `task_type` like `chunk_contextualization`) and set it to an OpenAI model optimized for cheap batch calls (per screenshot guidance: `gpt-4o-mini`).
- Add feature flags in `config/settings.py` to enable/disable contextualization at runtime (safe rollout).

### B) Ingestion-time contextual embeddings (core of Contextual Retrieval)

Modify `[packages/core/rag/llama_adapters/ingestion.py](packages/core/rag/llama_adapters/ingestion.py)`:

- In `_build_nodes(...)` (and `_build_nodes_from_chunks(...)` for cache hits):
  - For each chunk, call contextualizer to get:
    - `chunk_context`, `chunk_summary`, `chunk_type`, `section_title`, `concept_hint`
  - Store **raw chunk** for citations:
    - `metadata["text"] = chunk_text`
  - Store enrichment metadata:
    - `metadata["chunk_context"] = chunk_context`
    - `metadata["chunk_summary"] = chunk_summary`
    - `metadata["chunk_type"] = chunk_type`
    - `metadata["section_title"] = section_title`
    - `metadata["concept_hint"] = concept_hint`
  - Add a version marker for safe branching:
    - `metadata["contextual_version"] = 1`
  - Build **embedding text** (concatenation strategy; A/B-friendly):
    - `embed_text = chunk_context + "\n" + chunk_summary + "\n" + concept_hint + "\n\n" + chunk_text`
  - Keep `TextNode.text = embed_text` so Pinecone vector represents contextualized content.
  - Preserve existing metadata keys (`source_id`, `tenant_id`, `chunk_index`, `page_`*).

Why this matches the guide:

- The guide’s “prepend context before embedding” is achieved by embedding contextual fields + raw chunk.
- Raw chunk remains available for user-facing citations.

### C) Cache the generated contexts (to avoid paying repeatedly)

Extend the existing processed-PDF cache so repeated uploads of identical files don’t regenerate chunk contexts:

- `[packages/core/processing/context_cache.py](packages/core/processing/context_cache.py)`
  - Ensure cached `chunks` entries can store contextual metadata fields (`chunk_context`, `chunk_summary`, `chunk_type`, `section_title`, `concept_hint`) in each chunk’s metadata.
  - On cache hit, feed `chunks_with_metadata` into `ingest_chunks(...)` so contexts are reused.

### D) Lexical retrieval alignment (Contextual BM25 analogue)

Your Studio retrieval does not do lexical scoring, but **Chat does** (hybrid vector + keyword). Update hybrid keyword scoring to consider `chunk_context`:

- `[packages/core/rag/hybrid_retriever.py](packages/core/rag/hybrid_retriever.py)`
  - When building the text used for keyword scoring, use:
    - `keyword_text = (chunk_context + "\n" + chunk_summary + "\n" + concept_hint + "\n" + raw_text)` when available
    - fallback to `raw_text`
- Keep citations unchanged because citations use `metadata.text`.

This approximates the guide’s “Contextual BM25” without introducing a separate global BM25 index.

### E) Query decomposition + context-aware weighting (from screenshots; optional, production-gated)

These are not strictly required to meet the Contextual Retrieval guide, but your screenshots request them. Implement them behind feature flags so production rollout is safe.

1. **Query decomposition engine**

- At query time, derive:
  - `primary_concept`
  - `sub_queries[]` (2–5)
- Integrate into `retrieval_agents` so retrieval runs on (primary query + sub-queries) and merges results (similar to how Studio merges multiple retrieval queries).
- Target files: `[packages/core/rag/retriever.py](packages/core/rag/retriever.py)` and the existing agents in `packages/core/rag/agents/`.

1. **Context-aware retrieval weighting**

- After reranking, boost chunks whose `chunk_type` / `concept_hint` / `section_title` better match the query intent; penalize redundancy.
- This matches the screenshot note “plug after reranker”.

### F) Keep reranking as-is

- Chat already supports Cohere reranking via `[packages/core/rag/rerank/cohere_reranker.py](packages/core/rag/rerank/cohere_reranker.py)`.
- Studio currently does not rerank; we will **not** add reranking there in this iteration unless needed.

## Rollout / compatibility

- New documents ingested after the change will have contextualized embeddings.
- Old documents remain traditional; retrieval will be mixed until you choose to backfill later.
- All code paths should tolerate missing `metadata.chunk_context` (feature-gated by presence).
- Add feature flags so you can enable these independently:
  - ingestion contextualization (metadata + embedding concat)
  - hybrid keyword use of contextual fields
  - query decomposition
  - context-aware weighting

## Test plan (repo-local)

- Add/extend tests in `tests/` to validate:
  - Ingestion writes `metadata.text` unchanged and adds contextual fields (`chunk_context`, `chunk_summary`, `chunk_type`, `section_title`, `concept_hint`, `contextual_version`).
  - Embedded text contains the contextual fields + raw chunk in the intended order.
  - `HybridRetriever` keyword scoring uses contextual fields when present.
  - Feature-flag off path remains identical to current behavior.
- Add a small script or update an existing verification script (e.g. `scripts/verify_chunks_in_pinecone.py`) to sample a few vectors and print metadata keys.

## Observability

- Add pipeline trace spans for chunk-context generation during ingestion (similar to existing `StudioRetrieval/`* spans) so Analytics → Pipeline can show ingestion costs/latency.
- Record OpenAI usage with `feature_tag` like `chunk_contextualization` so cost dashboards separate it from normal chat/studio calls.
- Add counters: chunks contextualized, contextualization failures, average tokens per contextual field, and ingestion latency impact.

