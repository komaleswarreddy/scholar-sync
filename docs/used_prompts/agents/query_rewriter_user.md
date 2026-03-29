**Source:** `packages/core/prompts/templates/agents/query_rewriter_user.j2`

```jinja
{{ transcript_section }}## Current user message (this is what you must optimize retrieval for)
"{{ query }}"

## What to produce
Generate up to **{{ max_rewrites }}** distinct retrieval queries as specified in your system instructions.

### Quality checklist (apply before answering)
1. **Intent lock**: The first query must ask for the same information or task as the current message; do not drift to a related but different question.
2. **Coreference**: If the message uses "it", "that", "the above", "this concept", etc., replace with the specific topic or entity from the transcript when possible.
3. **Length**: Prefer concise search phrases (roughly 5–25 words for the primary query) unless the user's question is inherently long.
4. **Vocabulary**: Add 1–2 legitimate synonyms or technical alternates that appear in educational or domain text (e.g. "mitochondria" with "cellular respiration" only when the question clearly allows both).
5. **Abbreviations**: Expand common abbreviations when it helps matching (e.g. "DNA", "API") if the expansion is standard—not speculative.
6. **Noise**: Remove filler ("can you", "please", "I was wondering") from search strings when it does not change meaning.

### When the message is very short (one word or a fragment)
Still produce the best retrieval string: infer the minimal explicit question from context, or keep the fragment with clarifying nouns **only** if the transcript makes the referent obvious.

### Confidence calibration
- **High (0.8–1.0)**: Clear intent, transcript (if any) aligns, little ambiguity.
- **Mid (0.5–0.79)**: Some ambiguity or weak transcript; you did your best explicitly in queries[0].
- **Low (0.0–0.49)**: Highly ambiguous; queries[0] is your best conservative interpretation—do not invent specifics.

Return the JSON object now.
```
