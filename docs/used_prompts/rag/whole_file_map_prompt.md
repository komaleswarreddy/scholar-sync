**Source:** `packages/core/prompts/templates/rag/whole_file_map_prompt.j2`

```jinja
You are summarizing parts of a document for a later full-document summary.
For each Part below, write EXACTLY ONE concise sentence capturing its main idea.
Number your lines Part 1, Part 2, ... matching the order below.
Do not add an introduction or conclusion.

{{ excerpts }}
```
