**Source:** `packages/core/prompts/templates/studio/fallback_task_prompt.j2`

```jinja
Generate a {{ task_type }} based on: {% if context and context.strip() %}{{ context }}{% else %}general content{% endif %}

```
