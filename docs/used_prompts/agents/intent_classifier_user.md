**Source:** `packages/core/prompts/templates/agents/intent_classifier_user.j2`

```jinja
## Current user message (classify this)
{{ query }}

{{ context_block }}## Task
1. Read the current user message (use conversation context only to resolve references and follow-ups).
2. Choose exactly **one** `intent` slug from the system message list.
3. Set `confidence` to reflect how clear the intent is (see confidence rules in system message).
4. In `reasoning`, state in one or two short sentences **why** this label fits (cite what the user said or implied).

Respond with the JSON object only.
```
