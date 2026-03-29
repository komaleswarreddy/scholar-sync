**Source:** `packages/core/prompts/templates/studio/infographic_summary_bullets.j2`

```jinja
You summarize study takeaways for a student who just received an infographic from their document.

Output rules (strict):
- Return ONLY a valid JSON object with exactly this shape: {"bullets": ["...", "...", "...", "..."]}
- Use exactly **3 or 4** bullet strings (prefer 4 when the excerpt is rich).
- Each bullet: **one short sentence**, max 90 characters, plain language. Focus on **themes, relationships, or facts** the student should remember—not image layout, colors, or DALL·E.
- Ground bullets only in the excerpt below; do not invent facts.

Source excerpt:
{{ context }}
```
