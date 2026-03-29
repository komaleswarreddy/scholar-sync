**Source:** `packages/core/prompts/templates/agents/scope_narrower_user.j2`

```jinja
Analyze this query for information retrieval.{{ conversation_section }}
Query: {{ query }}

Extract key_terms (3-7), a focused_query string for retrieval (resolve references using conversation),
and max_chunks (3-15) suggested pool size.
```
