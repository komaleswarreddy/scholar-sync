# `packages/core` — full source inventory

This document maps **every Python and Jinja2 source file** under `packages/core` (134 files).  
**Excluded:** `__pycache__/`, `*.pyc`, and `database/migrations/versions/.gitkeep` (not code).

`packages/core` is the installable Python package (`scholarsync` / `packages.core` in `pyproject.toml`). It implements ingestion, RAG, chat (LangGraph), studio skills, security, memory, monitoring, DB models, and storage.

---

## Architecture (how pieces connect)

1. **Ingestion:** `services/source_service.py` → download S3 → optional `processing/context_cache` → PDF/text extract → **`rag/llama_adapters/ingestion.py`** → Pinecone (`vectorstores/pinecone_store.py`).
2. **Chat (LangGraph):** `langgraph/chat_graph.py` builds a `StateGraph` over `chat_state.ChatGraphState` → moderation → memory → answer cache → **`rag/retriever.py`** (Phase-2 agents + optional LlamaIndex adapter) → Cohere/MMR in graph → context → optional two-stage → **`llm`** generation → output agents → moderation → confidence → SSE-shaped events.
3. **Studio:** `services/studio_service.py` / `studio_feature_service.py` → `skills/*` + `prompts/templates/studio/*.j2` → `llm` / `image/dalle_client.py` for infographic.
4. **Observability:** `monitoring/metrics.py` → append JSONL under `logs/metrics/` (see `config/metrics_schema.json`).

---

## File index (every source file)

### `cache/`

| File | Role |
|------|------|
| `__init__.py` | Package init. |
| `client.py` | Cache client helpers. |
| `decorators.py` | Decorators for caching call results. |

### `compliance/`

| File | Role |
|------|------|
| `__init__.py` | Package init. |
| `audit.py` | Audit logging hooks for compliance. |
| `data_retention.py` | Data retention policies / helpers. |
| `privacy.py` | Privacy-related helpers. |

### `database/`

| File | Role |
|------|------|
| `__init__.py` | Re-exports DB utilities. |
| `connection.py` | Async SQLAlchemy engine/session (`get_db`). |

### `database/models/`

| File | Role |
|------|------|
| `__init__.py` | Model exports. |
| `alert_user_session.py` | SQLAlchemy model for alert/user session linkage. |
| `chat.py` | `Chat` and `Message` models (chat history persistence). |
| `guardrail_user_block.py` | Guardrail block / user state model. |
| `note.py` | User notes model. |
| `source.py` | `Source` model (upload metadata, status, S3 key). |
| `tenant.py` | Tenant model. |
| `user.py` | User model. |

### `evaluation/`

| File | Role |
|------|------|
| `__init__.py` | Package init. |
| `cold_start_handler.py` | Cold-start / low-context handling for chat quality. |
| `confidence_scorer.py` | Scores answer confidence from query, answer, citations. |
| `evaluator.py` | Continuous evaluation loop, metrics enums, `EvaluationReport`. |
| `scheduler.py` | Schedules periodic eval runs. |

### `guardrails/`

| File | Role |
|------|------|
| `__init__.py` | Package init. |
| `budget_enforcer.py` | Enforces token/cost budgets. |
| `cost_manager.py` | Tracks / limits LLM cost in a session or request. |
| `input_guardian.py` | Input-side guardrail orchestration. |
| `output_moderator.py` | Output-side moderation helpers. |

### `image/`

| File | Role |
|------|------|
| `__init__.py` | Package init. |
| `dalle_client.py` | OpenAI DALL·E client for infographic images. |

### `langgraph/`

| File | Role |
|------|------|
| `__init__.py` | Docstring: LangGraph chat orchestration. |
| `chat_graph.py` | **`LangGraphChatPipeline`**: graph nodes (ModerationInput → Memory → Cache → Retrieval → RerankerMMR → ContextSelector → Generate → OutputAgents → ModerationOutput → Evaluator), `stream()` yields SSE-shaped dicts. |
| `chat_state.py` | **`ChatGraphState`**: `TypedDict` of all state keys for the graph. |

### `llm/`

| File | Role |
|------|------|
| `__init__.py` | Exports clients, factory, `LLMProvider`. |
| `_base.py` | Abstract `LLMClient`, `LLMResponse`, streaming chunk types. |
| `factory.py` | **`get_llm_client`**, **`get_model_for_task`**, model enum, Gemini 1.5-flash retirement handling. |
| `gemini_client.py` | Google Gemini `generate` / streaming integration + metrics. |
| `openai_client.py` | OpenAI chat completions + embeddings + metrics. |

### `memory/`

| File | Role |
|------|------|
| `__init__.py` | Exports memory helpers used by chat/RAG. |
| `answer_cache.py` | Disk-backed answer cache keyed by query + source ids. |
| `chat_summarizer.py` | Summarizes long chat history when over threshold. |
| `context_compressor.py` | Compresses context strings to save tokens. |
| `conversation_memory.py` | Conversation memory structures / helpers. |
| `memory_manager.py` | Prunes history by tokens/messages/strategy. |
| `rate_limiter.py` | Per-user rate limit + debounce for chat API. |
| `retrieval_cache.py` | Caches query rewrites and rerank results under `cache/retrieval/`. |
| `summarizer.py` | Generic summarization helper. |

### `monitoring/`

| File | Role |
|------|------|
| `__init__.py` | Package init. |
| `alerts.py` | Alert definitions / firing helpers. |
| `logger.py` | App logging setup. |
| `metrics.py` | **`MetricsCollector`**: JSONL persistence under `logs/metrics/`, in-memory deques. |
| `slo.py` | SLO checking vs targets. |

### `orchestrator/`

| File | Role |
|------|------|
| `__init__.py` | Package init. |
| `context_builder.py` | Builds consolidated context for LLM from chunks. |
| `executor.py` | Executes multi-step orchestration tasks. |
| `model_selector.py` | Selects model/provider for a task. |
| `task_router.py` | Routes tasks to handlers (studio vs chat patterns). |

### `policies/`

| File | Role |
|------|------|
| `__init__.py` | Package init. |
| `enforcement.py` | Policy enforcement hooks (tenant/feature). |

### `processing/`

| File | Role |
|------|------|
| `__init__.py` | Package init. |
| `context_cache.py` | **`ContextCache`**: hashes file bytes → cached chunks/text under `cache/processed_pdfs/{tenant}`. |
| `pdf_preprocessor.py` | Cleans/normalizes PDF-extracted text to reduce tokens. |
| `semantic_chunker.py` | Semantic splitting utilities (used with chunker settings). |

### `prompts/`

| File | Role |
|------|------|
| `__init__.py` | Exports `load_prompt` and registry. |
| `loader.py` | Loads Jinja2 templates from `templates/`. |
| `registry.py` | Registers named prompts. |
| `templates/chat/rag_prompt.j2` | RAG chat template: document context + current message + optional **conversation mode** transcript (`conversation_transcript`, `has_prior_conversation`). |
| `templates/studio/flashcards_prompt.j2` | Flashcard generation prompt. |
| `templates/studio/infographic_prompt.j2` | Infographic brief + structure prompt. |
| `templates/studio/mind_map_prompt.j2` | Mind map JSON/hierarchy prompt. |
| `templates/studio/quiz_prompt.j2` | Quiz JSON prompt. |
| `templates/studio/report_prompt.j2` | Report generation prompt. |
| `templates/studio/slide_deck_prompt.j2` | Slide deck outline/content prompt. |

### `rag/`

| File | Role |
|------|------|
| `__init__.py` | RAG package exports. |
| `chunker.py` | **`Chunker`**: splits text into chunks with overlap (semantic option). |
| `embedder.py` | **`Embedder`**: OpenAI embeddings for queries/chunks. |
| `hybrid_retriever.py` | **`HybridRetriever`**: merges vector + keyword signals with weights. |
| `retriever.py` | **`Retriever`**: main retrieval pipeline; Phase-2 agents; optional **`LlamaIndexRetrievalAdapter`**; `RetrievalCache`; follow-up detection; debug trace. |
| `vector_store.py` | Facade / helpers around vector operations (legacy compatibility). |

### `rag/agents/`

| File | Role |
|------|------|
| `__init__.py` | Exports agent classes and `UserIntent`. |
| `citation_enforcer.py` | Checks that claims align with citation list. |
| `context_deduper.py` | Removes near-duplicate chunks. |
| `context_selector.py` | Selects chunks within token budget (`CONTEXT_TOKEN_BUDGET`). |
| `early_stop_detector.py` | Detects when answer can stop early. |
| `intent_classifier.py` | Classifies query intent for top-k and routing. |
| `mmr_diversity.py` | Maximal Marginal Relevance for diverse chunks. |
| `output_formatter.py` | Formats answer (bullets, numbered, etc.). |
| `output_length_limiter.py` | Truncates by tokens/chars/sentences. |
| `query_complexity_scorer.py` | Marks simple vs complex queries to skip expensive steps. |
| `query_rewriter.py` | LLM rewrites query; uses cache. |
| — | Reranking is **Cohere-only** (`rag/rerank/cohere_reranker.py`, used by `Retriever`). |
| `scope_narrower.py` | Narrows query scope / extracts key terms. |
### `rag/llama_adapters/`

| File | Role |
|------|------|
| `__init__.py` | Exports ingestion + retrieval adapters. |
| `ingestion.py` | **`LlamaIndexIngestionAdapter`**: SentenceSplitter, TextNodes, Pinecone upsert, stable ids `{source_id}_chunk_{i}`. |
| `retrieval.py` | **`LlamaIndexRetrievalAdapter`**: VectorStoreIndex retriever → `matches` list shape. |

### `rag/rerank/`

| File | Role |
|------|------|
| `cohere_reranker.py` | **`CohereReranker`**: calls Cohere rerank API, maps back to match dicts. |

### `rag/vectorstores/`

| File | Role |
|------|------|
| `__init__.py` | Exports Pinecone store. |
| `base.py` | Abstract vector store interface. |
| `pinecone_store.py` | **`PineconeVectorStore`**: query, upsert, delete by source, namespace = tenant. |

### `security/`

| File | Role |
|------|------|
| `__init__.py` | Exports moderation, detectors, gates, templates. |
| `encryption.py` | At-rest / field encryption helpers. |
| `file_validator.py` | Validates uploads (type, size). |
| `injection_detector.py` | Prompt-injection heuristics / scoring. |
| `intent_gate.py` | Academic-only intent gating. |
| `openai_moderation.py` | Wraps OpenAI Moderation API; category score helpers. |
| `pii_detector.py` | Detects/redacts PII. |
| `refusal_templates.py` | **`RefusalTemplates`**, `RefusalReason` enum. |
| `restricted_retriever.py` | Retrieval constrained to approved sources (syllabus lock). |
| `safety_filter.py` | Keyword/rule-based safety on input/output. |
| `secrets_manager.py` | Loads secrets (env / cloud patterns). |

### `services/`

| File | Role |
|------|------|
| `__init__.py` | Service exports. |
| `chat_service.py` | **`ChatService`**: CRUD chats/messages, feedback helpers. |
| `note_service.py` | **`NotesService`**: create/list/get/update/delete notes. |
| `source_service.py` | **`IngestionService`**: upload, `process_file_background`, list/delete sources, PDF/text extract, LlamaIndex ingestion. |
| `studio_feature_service.py` | Feature-level studio orchestration (metrics, routing). |
| `studio_service.py` | Studio generation entry: task types, context from Pinecone, model routing. |

### `skills/`

| File | Role |
|------|------|
| `__init__.py` | Skill registry exports. |
| `base.py` | Base class for studio skills. |
| `chat_skill.py` | Thin chat skill helper (if used by orchestrator). |
| `flashcard_skill.py` | Flashcard JSON generation. |
| `infographic_skill.py` | Infographic brief + optional DALL·E image. |
| `mindmap_skill.py` | Mind map hierarchical data. |
| `quiz_skill.py` | Quiz JSON generation. |
| `report_skill.py` | Long-form report. |
| `slidedeck_skill.py` | Slide deck structured content. |

### `storage/`

| File | Role |
|------|------|
| `__init__.py` | Storage backend exports. |
| `base.py` | Abstract storage interface. |
| `local.py` | Local filesystem storage (dev). |
| `s3.py` | **`S3Storage`**: Supabase/S3 upload, download, presigned URLs, delete. |

### `utils/`

| File | Role |
|------|------|
| `__init__.py` | Utils exports. |
| `exceptions.py` | Shared exception types. |
| `files.py` | File helpers (hash, mime). |
| `formatting.py` | String/format helpers. |
| `tokens.py` | Token counting / estimation helpers. |

---

## Notes

- **`rag_service.py`** is not present in source (removed per git history); chat uses **`LangGraphChatPipeline`** when `USE_LANGGRAPH_CHAT` is on (`apps/api/routes/chat.py`).
- **Line counts** and behavior of each module can drift; this file is an **inventory + map**, not a substitute for reading diffs when you change behavior.

---

*Generated as a full-file inventory of `packages/core` source (134 files).*
