# Used prompts (mirror of `packages/core/prompts/templates`)

This folder documents Jinja prompt templates under [`packages/core/prompts/templates`](../../packages/core/prompts/templates).

- **Per-template docs:** Each subdirectory matches that tree (`studio/`, `chat/`, `agents/`, `rag/`). Each `.md` pairs with one `.j2` file (same basename) and includes a **verbatim copy** of the template body in a fenced block, plus the canonical source path.

Templates are rendered with `packages.core.prompts.load_prompt(template_path, **kwargs)` unless a given file’s header says otherwise.

## Index by area

| Area | Folder |
|------|--------|
| Studio | [`studio/`](./studio/) |
| Chat | [`chat/`](./chat/) |
| Agents | [`agents/`](./agents/) |
| RAG | [`rag/`](./rag/) |

## Quick reference — `load_prompt` call sites

| Template path | Called from |
|---------------|-------------|
| `studio/quiz_prompt.j2` | `packages/core/services/studio_service.py` — `_generate_structured_task` |
| `studio/flashcards_prompt.j2` | same |
| `studio/mind_map_prompt.j2` | same |
| `studio/slide_deck_prompt.j2` | same |
| `studio/system_educational_json_markdown.j2` | same (system prompt) |
| `studio/report_prompt.j2` | `studio_service.py` — report path |
| `studio/system_educational_markdown_fallback.j2` | same (system prompt) |
| `studio/infographic_summary_bullets.j2` | `studio_service.py` — `_infographic_learner_bullets` |
| `studio/infographic_structured_prompt.j2` | `studio_service.py` — `_generate_infographic` |
| `chat/direct_chat.j2` | `packages/core/langgraph/chat_graph.py` — `_node_direct_chat` |
| `chat/rag_prompt.j2` | `chat_graph.py` — RAG node |
| `chat/chat_summarizer_prompt.j2` | `packages/core/memory/chat_summarizer.py` |
| `agents/intent_classifier_system.j2` | `packages/core/rag/agents/intent_classifier.py` |
| `agents/intent_classifier_user.j2` | same |
| `agents/query_rewriter_system.j2` | `packages/core/rag/agents/query_rewriter.py` |
| `agents/query_rewriter_user.j2` | same |
| `rag/whole_file_reduce_prompt.j2` | `packages/core/rag/whole_file_map_reduce.py` — `_reduce_summaries` |

Some templates exist on disk but are not passed to `load_prompt` in Python (see the note at the top of those `.md` files).
