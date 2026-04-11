---
name: admin-trace-visibility
overview: Add a structured, admin-friendly trace explainer for each chat Trace ID, showing exactly which sources/namespaces were searched, which chunks were retrieved/selected, how the prompt context was built (selected vs global), and a deterministic decision log for why the system answered vs returned “Not found in provided sources.”
todos:
  - id: backend-trace-artifacts
    content: Add per-trace artifact storage to PipelineTraceStore and capture retrieval + context-selector chunk descriptors plus request flags (active_source_ids, include_ncert_global, ncert filters).
    status: completed
  - id: backend-explain-endpoint
    content: Add GET /api/v1/pipeline-traces/{trace_id}/explain to compute structured explain payload (sources searched, chunks retrieved/selected, prompt breakdown, decision log, answer origin).
    status: completed
  - id: frontend-explainer-ui
    content: Extend analytics pipeline page to render the explain panel (answer origin badge, sources table, chunks table w/ included flag, prompt breakdown, decision log) while keeping existing span timeline/table.
    status: completed
  - id: validation-and-caps
    content: Add payload size caps + redaction rules; validate the three “Not found…” conditions and verify NCERT fallback is explicitly explained.
    status: completed
isProject: false
---

## Goal
Expose an **admin-only, structured** explanation of how each response was produced for a given `trace_id` (without removing any existing pipeline trace UI).

## What exists today (baseline)
- Pipeline trace capture is **in-memory** and span-based in [`packages/core/monitoring/pipeline_trace.py`](packages/core/monitoring/pipeline_trace.py) with node summaries only (counts, previews).
- Trace API returns spans + token/cost usage in [`apps/api/routes/pipeline_traces.py`](apps/api/routes/pipeline_traces.py).
- Admin UI pipeline page renders spans + raw `input_summary`/`output_summary` JSON in [`apps/web/src/app/analytics/pipeline/page.tsx`](apps/web/src/app/analytics/pipeline/page.tsx).
- Retrieval output already contains key discriminators:
  - `state.active_source_ids`, `state.include_ncert_global`, `state.ncert_*` in [`packages/core/langgraph/chat_state.py`](packages/core/langgraph/chat_state.py)
  - `state.selected_matches` built in `ContextSelector` and used to build `state.context` + `state.citations` in [`packages/core/langgraph/chat_graph.py`](packages/core/langgraph/chat_graph.py)
  - NCERT global merge normalizes metadata with `source_type='ncert_global'` and `knowledge_namespace='NcertDataGlobal'` in [`packages/core/rag/retriever.py`](packages/core/rag/retriever.py)

## Design
### 1) Add a new “trace explain” payload (backend computed)
Add a new endpoint:
- `GET /api/v1/pipeline-traces/{trace_id}/explain`
  - **Owner** can view
  - **Admin** can view anyone
  - Response includes the existing trace payload plus a new `explain` object.

`explain` will be computed from the stored spans’ summaries (and newly-added trace artifacts), plus DB lookups:
- `sources_searched[]`: `{source_id, source_title, file_name, namespace, source_kind}`
  - **Tenant sources**: from `sources` table (`title`, `s3_key` → file name via basename)
  - **NCERT global**: from `ncert_global_documents` (`title`, `original_filename`, `pinecone_namespace`)
- `retrieval_steps[]`: normalized list from spans (e.g. `Retrieval/query_rewrite`, `Retrieval/embedding`, `Retrieval/simple_vector_query`, `Retrieval/simple_cohere_rerank`, `ContextSelector`, `Generate`, etc.)
- `chunks[]`: one row per retrieved/selected chunk
  - `{chunk_id, source_id, source_title, namespace, source_kind, score, preview, included_in_prompt}`
  - `preview` from `metadata.text` truncated
  - `included_in_prompt` = whether in `selected_matches`
- `prompt_breakdown` (structured-only per your choice):
  - `user_query`
  - `selected_sources_context` (rendered from selected matches that are tenant sources)
  - `global_context` (rendered from selected matches that are NCERT/global)
  - `final_context_sent_to_llm` (the exact `state.context` string)
- `answer_origin`: one of `{selected_only, global_only, combined, none}`
  - based on which categories appear in `selected_matches` and/or `state.include_ncert_global`
- `decision_log[]`: deterministic reasons, e.g.
  - `selected_source_retrieval`: counts + max score vs threshold
  - `global_fallback_enabled`: boolean + which namespace used
  - `final_context_contains_selected_sources`: boolean
  - `final_answer_classification`: answered vs `Not found in provided sources.`

### 2) Capture the missing raw data needed to compute `explain`
Currently, the trace store doesn’t retain:
- `active_source_ids`, `include_ncert_global`, `ncert_*`
- `matches`/`selected_matches` details (chunk ids, scores, metadata)

Add a small “artifact capture” mechanism to the trace store:
- Extend [`packages/core/monitoring/pipeline_trace.py`](packages/core/monitoring/pipeline_trace.py) to support per-trace **artifacts** (stored alongside `TraceRecord`), gated by a size cap.
- Update LangGraph nodes (in [`packages/core/langgraph/chat_graph.py`](packages/core/langgraph/chat_graph.py)) to attach artifacts at key points:
  - After `Retrieval`: store `active_source_ids`, `include_ncert_global`, `ncert_*`, and a lightweight list of retrieved chunk descriptors.
  - After `ContextSelector`: store `selected_matches` descriptors and the built `context` string length.

Artifact descriptor shape (kept compact):
- `chunk_descriptor`: `{id, score, metadata: {source_id, source_type, knowledge_namespace, page_number/page_start, text_preview}}`

### 3) Make admin source-title lookups work cross-user
Today `_load_source_titles` in [`packages/core/langgraph/chat_graph.py`](packages/core/langgraph/chat_graph.py) filters by `Source.user_id == self.user_id`, which breaks admin viewing other users’ traces.

For the new `explain` endpoint, do DB lookups with:
- tenant constraint for tenant sources (`tenant_id == trace.tenant_id`)
- **no user_id constraint** when caller is admin

### 4) Implement the “Not found in provided sources” conditions as an explicit decision model
Codify your 3 conditions in the `decision_log` computation:
- **Threshold check**: compare best tenant chunk score to `settings.SIMILARITY_THRESHOLD`.
- **Weak/unrelated**: if tenant chunks exist but were excluded from `selected_matches` (or `selected_matches` contain only global chunks).
- **No selected-source context**: `selected_matches` contains 0 tenant chunks.

This does not change the existing behavior; it makes it observable and consistent in admin.

### 5) Frontend: add a structured explainer panel (do not remove existing trace UI)
In [`apps/web/src/app/analytics/pipeline/page.tsx`](apps/web/src/app/analytics/pipeline/page.tsx):
- Keep the current spans timeline/table.
- Add a new section “Trace explanation” above/alongside span details:
  - **Answer origin** badge: selected/global/combined/none
  - **Sources searched** table
  - **Chunks** table with filters:
    - show `included_in_prompt` yes/no
    - group by source
  - **Prompt breakdown** (structured-only): user query + selected context + global context + final context
  - **Decision log** list (human readable)

Add a small client type for the new payload and a new api-client method:
- [`apps/web/src/lib/api-client.ts`](apps/web/src/lib/api-client.ts): `getPipelineTraceExplain(traceId)`

### 6) Safety / size limits
- Add caps to avoid huge payloads:
  - max chunks returned (e.g. first 200 retrieved, first 80 selected)
  - previews trimmed (e.g. 240–400 chars)
  - prompt breakdown uses the already-truncated context entries built by `ContextSelector`

### 7) Test plan (dev)
- Trigger three scenarios and verify the explainer:
  - Selected sources only (no NCERT)
  - NCERT enabled and merged (combined)
  - No relevant tenant evidence → “Not found…” (ensure decision log matches your 3 conditions)

## Key files to change
- Backend trace store: [`packages/core/monitoring/pipeline_trace.py`](packages/core/monitoring/pipeline_trace.py)
- Chat pipeline capture points: [`packages/core/langgraph/chat_graph.py`](packages/core/langgraph/chat_graph.py)
- Trace API: [`apps/api/routes/pipeline_traces.py`](apps/api/routes/pipeline_traces.py)
- Source/NCERT DB lookups: [`packages/core/database/models/source.py`](packages/core/database/models/source.py), [`packages/core/database/models/ncert_global.py`](packages/core/database/models/ncert_global.py)
- Admin UI: [`apps/web/src/app/analytics/pipeline/page.tsx`](apps/web/src/app/analytics/pipeline/page.tsx)
- Client API: [`apps/web/src/lib/api-client.ts`](apps/web/src/lib/api-client.ts)
