**Source:** `packages/core/prompts/templates/rag/whole_file_reduce_prompt.j2`

```jinja
You are writing the final answer for the user.
Below are ordered summaries of every section/part of their document(s).
Write a clear, well-structured response that answers their request and reflects the ENTIRE document, not just the beginning. Use sections or bullet points if helpful.
Do not include citation markers like [1]. Do not paste raw excerpt lists.

User request:
{{ user_message }}

Section summaries (in document order):
{{ section_summaries }}
```
