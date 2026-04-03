# Contextual Retrieval in this Project (Before vs After)

This document explains how the system worked **before** Contextual Retrieval, what we **implemented**, and how the **current system works** after the changes. It includes flow diagrams for ingestion and query-time retrieval, **feature flags**, and **real-world before/after examples**.

---

## What “Contextual Retrieval” means here

Contextual Retrieval (as described in `docs/contextual_retrieval_guide_markdown_conversion.md`) combines:

- **Contextual Embeddings**: generate a short, chunk-specific context and prepend it before embedding.
- **Contextual BM25 / lexical signal**: matching benefits from contextual fields (exact terms, entities, codes), plus optional **BM25 + rank fusion** with dense retrieval.
- **Reranking**: rerank candidate chunks (Cohere) before final context packing.
- **Optional upgrades** (production-gated): intent-based retrieval breadth, query decomposition, metadata-based score adjustment **after** rerank.

In this repo, these layers are implemented with feature flags and production guardrails.

---

## BEFORE (Traditional RAG in this repo)

### Ingestion flow (before)

Key properties:

- Chunk text stored + embedded as **raw chunk only**.
- No chunk-level context metadata (`chunk_context`, `concept_hint`, etc.).

```mermaid
flowchart LR
  A[Upload PDF/Doc] --> B[Extract + Clean Text]
  B --> C[Chunking]
  C --> D[Embed raw chunk text]
  D --> E[Upsert vectors to Pinecone]
```

### Query-time flow (before)

Key properties:

- Vector retrieval finds “semantically similar” chunks, but can miss:
  - exact technical strings (codes, IDs)
  - chunks that need surrounding document context to be understood
- Keyword scoring (if used) is limited to raw chunk text.
- Fixed retrieval breadth: no intent-specific widening/narrowing.

```mermaid
flowchart LR
  Q[User Query] --> E1[Embed Query]
  E1 --> V[Vector Search (Pinecone)]
  V --> H[Hybrid merge (limited)]
  H --> R[Reranker (Cohere)]
  R --> Ctx[Context selection]
  Ctx --> LLM[LLM Answer]
```

---

## AFTER (Contextual Retrieval system in this repo)

### What we implemented (high-level)

- **Chunk contextualizer (OpenAI)**:
  - Generates: `chunk_context`, `chunk_summary`, `chunk_type`, `section_title`, `concept_hint`
  - Prompt template: `packages/core/prompts/templates/rag/chunk_contextualization.j2`
  - Implementation: `packages/core/rag/contextual_retrieval/contextualizer.py`

- **Contextual embeddings (ingestion-time)**:
  - We keep raw chunk text in `metadata["text"]` for citations (unchanged citations).
  - We embed a concatenated text:

    \[
    embed\_text = chunk\_context + chunk\_summary + concept\_hint + raw\_chunk
    \]

  - Stored marker: `metadata["contextual_version"] = 1`
  - Integration: `packages/core/rag/llama_adapters/ingestion.py`
  - **Observability**: ingestion spans can report `chunks_skipped_already_contextualized` and `chunks_empty_summary_after_enrich` (see pipeline trace for `Ingestion/ContextualizeChunks`).

- **Contextual BM25 / hybrid keyword**:
  - **Keyword scoring** uses: `(chunk_context + chunk_summary + concept_hint + raw_text)` so lexical matches benefit from context.
  - Optional **BM25 + Rank Fusion (RRF)** (when not using LlamaIndex retrieval path for that branch): build a local BM25 index over fetched chunks, fuse with dense hits, then pass through hybrid normalization.
  - Implementation: `packages/core/rag/bm25_fusion.py`, `packages/core/rag/hybrid_retriever.py`, `packages/core/rag/retriever.py`
  - Dependency: `rank-bm25`

- **Reranker**:
  - Cohere reranking: `packages/core/rag/rerank/cohere_reranker.py`

- **Intent-gated retrieval strategy** (query-time, no extra LLM when LangGraph already classified intent):
  - Uses `classified_intent` + **`intent_classification_confidence`** from the graph to widen or narrow **initial retrieval** (`initial_retrieval_k_multiplier`), gate **optional query decomposition**, and scale the **MMR candidate pool** (`mmr_target_multiplier`).
  - Low confidence falls back to **neutral** multipliers (legacy-style behavior).
  - Implementation: `packages/core/rag/retrieval_strategy.py`, wired in `packages/core/rag/retriever.py`.

- **Query decomposition** (optional):
  - Adds sub-queries for multi-facet questions when strategy + flags allow; **`ENABLE_QUERY_DECOMPOSITION_SHADOW`** logs decomposition without changing retrieval queries (staging).

- **Context-aware retrieval weighting** (optional):
  - **Runs after Cohere rerank** (not after hybrid merge): small score boosts when `concept_hint` / `chunk_type` align with the query, then re-sort before the context selector.
  - Implementation: `packages/core/rag/context_aware_weighting.py`

---

## AFTER: Ingestion flow (Contextual Embeddings)

Key properties:

- Each chunk gets compact contextual metadata.
- Embeddings are computed from contextualized text.
- **Citations remain raw** because the UI / downstream references `metadata["text"]`.

```mermaid
flowchart LR
  A[Upload PDF/Doc] --> B[Extract + Clean Text]
  B --> C[Chunking]
  C --> D[Chunk Contextualization (OpenAI)]
  D --> M[Store contextual fields in metadata]
  D --> P[Prepend context to build embed_text]
  P --> E[Embed contextualized text]
  E --> U[Upsert vectors to Pinecone]
  M --> U
```

### Stored metadata (per chunk)

- **Always present**:
  - `metadata.text` (raw chunk for citations)
  - `metadata.source_id`, `metadata.tenant_id`, `metadata.chunk_index`, optional page fields
- **Contextual Retrieval fields** (when enabled):
  - `metadata.chunk_context`
  - `metadata.chunk_summary`
  - `metadata.chunk_type`
  - `metadata.section_title`
  - `metadata.concept_hint`
  - `metadata.contextual_version = 1`

---

## AFTER: Query-time flow (current default + optional stages)

### Default “After” pipeline (conceptual)

LangGraph supplies **intent + confidence**; the retriever applies **retrieval strategy**, then rewrite, embedding, retrieval, MMR, rerank, optional post-rerank metadata weighting, then context selection.

```mermaid
flowchart LR
  Q[User Query] --> I[Intent + confidence from LangGraph]
  I --> ST[Retrieval strategy multipliers]
  ST --> RW[Query rewrite]
  RW --> DQ[Optional query decomposition]
  DQ --> E1[Embed primary query]
  E1 --> V[Vector search]
  V --> HY[Hybrid keyword uses contextual fields]
  HY --> MMR[MMR diversity]
  MMR --> R[Cohere rerank]
  R --> CAW[Optional context-aware weighting]
  CAW --> S[Context selector]
  S --> LLM[LLM Answer]
```

### Optional: BM25 + Rank Fusion (RRF)

When `ENABLE_BM25_RANK_FUSION=true` (and the Pinecone path is used for that branch), dense and sparse lists are fused before the hybrid keyword stage narrows/normalizes scores on the candidate pool:

```mermaid
flowchart LR
  Q[User Query] --> E1[Embed Query]
  E1 --> Dense[Dense retrieval (Pinecone vector)]
  Q --> BM25[BM25 over fetched chunk corpus]
  Dense --> Fuse[Rank Fusion (RRF) Top N]
  BM25 --> Fuse
  Fuse --> HY[Hybrid normalize scores]
  HY --> MMR[MMR]
  MMR --> R[Cohere rerank]
  R --> CAW[Optional context-aware weighting]
  CAW --> LLM[LLM Answer]
```

---

## Real-world examples: BEFORE vs AFTER

These are illustrative of how the same **user question** behaves under the old vs current stack. Exact ranking depends on your corpus and flags.

### 1) Vague or “indirect” concept question (needs document context)

| | **Example** |
|---|-------------|
| **User** | *“According to my notes, why does the author say the first phase matters?”* |
| **Before** | The chunk that contains the answer might only say *“This phase establishes the baseline…”* without repeating “first phase” or the author’s framing. **Dense search** under-matches; **keyword** on raw text alone may miss synonyms. |
| **After** | `chunk_context` / `chunk_summary` often mention the section and topic, so **embedding** and **hybrid keyword** both see richer cues. **Rerank** then picks the best-evidence chunk. **Use case**: chapter-heavy PDFs, indirect follow-ups. |

### 2) Exact string, SKU, or course code in a long document

| | **Example** |
|---|-------------|
| **User** | *“Where does the manual mention error code E-204?”* |
| **Before** | If the code sits in a short chunk with little semantic “surrounding” text, **vector-only** recall can be brittle. |
| **After** | `concept_hint` and contextual lines often repeat entities; **hybrid** + optional **BM25+RRF** improve **lexical recovery**. **Rerank** still decides final order. **Use case**: lab manuals, syllabi, technical PDFs. |

### 3) Compare / contrast across the source

| | **Example** |
|---|-------------|
| **User** | *“Compare Method A and Method B from the handout.”* |
| **Before** | One embedding of the question might pull chunks strong on A but weak on B (single-query bias). |
| **After** | With confident **`comparison`** intent, **retrieval strategy** widens the **initial candidate pool** so both sides are more likely in the pool before **MMR** and **rerank**. With **`ENABLE_QUERY_DECOMPOSITION`** (and strategy allowing it), **extra sub-queries** can further improve recall. **Use case**: exam prep, structured notes. |

### 4) Short definition-style question

| | **Example** |
|---|-------------|
| **User** | *“What is oxidative phosphorylation?”* |
| **Before** | Same broad **top_k** scaling as long essay questions → more noise in the pool. |
| **After** | Confident **`definition`** intent uses a **tighter initial multiplier** (fewer, more focused candidates), then **rerank** + **optional post-rerank** boost for `chunk_type: definition` when the query looks definitional. **Use case**: flashcard-style Q&A from textbooks. |

### 5) Long explanation + real-life framing (still grounded in sources)

| | **Example** |
|---|-------------|
| **User** | *“Explain reflex arcs using a real-life burn example.”* |
| **Before** | Retrieval depends on whether the **source** actually contains “reflex” / “spinal cord”; if yes, raw RAG can still answer well. If chunks are thin on keywords, recall is weaker. |
| **After** | Contextual metadata improves **matching** to the right passages; **explanation** intent with enough words can enable **decomposition** (when flags on) to retrieve both “reflex pathway” and “example” facets. The **LLM** still must stay grounded in `metadata.text` citations. **Use case**: applied biology/psych explanations tied to uploaded material. |

---

## Why the current system is better than before

- **Better recall for “hard” queries**:
  - Raw chunks sometimes lack the surrounding context required to match the query.
  - Contextual embeddings add a short “where this sits in the document” signal, so semantic retrieval becomes more reliable.

- **Better exact-term retrieval**:
  - Technical identifiers and exact strings are easier to find when `concept_hint` + contextual fields participate in keyword scoring.
  - With BM25 rank-fusion enabled, the system can recover chunks that embeddings might miss.

- **Stacked improvements**:
  - Dense retrieval + (optional) BM25 fusion + hybrid + MMR + reranking + (optional) metadata polish after rerank compound for final context quality.

- **Intent-aware breadth (production-gated)**:
  - Comparison/analysis-style questions can fetch a wider initial pool when the classifier is confident; definitions can stay tighter—without a second intent LLM in the retriever when the graph already classified the message.

- **Citations remain clean**:
  - Even though embeddings use contextualized text, the user-facing citation snippet stays based on `metadata["text"]` (raw chunk), avoiding “invented” quoted passages in the index.

---

## Feature flags and production controls

| Flag / setting | Role |
|----------------|------|
| `ENABLE_CONTEXTUAL_RETRIEVAL_INGESTION` | Ingestion-time contextualization on/off |
| `ENABLE_BM25_RANK_FUSION` | BM25 + RRF fusion stage (guide-like), subject to retriever branch |
| `RETRIEVAL_INTENT_ROUTING_MIN_CONFIDENCE` | Below this, use **neutral** retrieval multipliers |
| `QUERY_DECOMPOSITION_MIN_QUERY_WORDS_EXPLANATION` | Word-count gate for explanation-intent decomposition |
| `ENABLE_QUERY_DECOMPOSITION` | Append sub-queries to retrieval (when strategy allows) |
| `ENABLE_QUERY_DECOMPOSITION_SHADOW` | Run decomposer for traces only; **do not** mutate query list |
| `ENABLE_CONTEXT_AWARE_RETRIEVAL_WEIGHTING` | Post-**rerank** metadata boosts (`CONTEXT_AWARE_WEIGHTING_MAX_BOOST`) |

Guardrails include:

- Concurrency + retries for contextualization
- Input size caps (doc/chunk prompt size)
- Candidate caps for BM25 corpus (e.g. `BM25_CORPUS_MAX_CHUNKS`)
- Rerank cache remains **pre–metadata-boost**; boosts apply after cache read for consistent behavior

---

## Smoke test script (developer)

You can reproduce “before vs after” quickly using:

- `scripts/smoke_contextual_retrieval.py`
  - Ingest one document twice under two `source_id`s (baseline vs contextual)
  - Query both and compare returned chunk metadata (look for `contextual_version=1`, `concept_hint`, etc.)
  - Optional: `--classified-intent`, `--intent-confidence`, `--context-aware-weighting`, `--rag-debug` to inspect `retrieval_strategy` and guardrails in `debug_trace`
