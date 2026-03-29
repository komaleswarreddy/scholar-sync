**Source:** `packages/core/prompts/templates/studio/infographic_prompt.j2`

```jinja
You are preparing ONE final prompt for OpenAI DALL-E 3. The image must be a **high-quality educational study graphic** that helps a student **understand the selected PDF excerpt in seconds**—not abstract wall art, not a decorative poster, and not a maze of random lines.

**Grounding (critical):**
- The visual must **directly represent the actual ideas** in the source excerpt: key terms, steps in a **process**, **comparisons**, **causal links**, **ordered stages**, or **how a few concepts relate**. Every main shape or stage should map to something the excerpt discusses.
- **Pick ONE clear format** that fits the excerpt best (state which in the DALL-E prompt): **(A)** linear **process flow** (left-to-right or top-to-bottom), **(B)** **two-column comparison** of two main ideas, **(C)** **timeline** with 3–6 ordered events or stages, or **(D)** a **small concept map** (3–6 nodes) showing relationships. Do **not** mix many unrelated topics in one image.

**Clarity vs. decoration:**
- Use **clean instructional schematic style** (flat vector, like a textbook diagram or modern study sheet): **straight or gently curved connectors**, obvious direction of flow, generous spacing.
- **Forbidden:** tangled “circuit board” paths, maze-like wiring, random plus/minus signs, dots-as-decor, meaningless symbols, ornate borders, or generic icons that do not match the excerpt’s concepts.
- **No photorealism**, no microscopic detail, no cramming the entire document into one image.

**Text in the image (DALL-E limitation — still keep it tight):**
- Use **only short labels** copied or closely paraphrased from **terms that appear in the source** (anatomical parts, process names, etc.). **No paragraphs, no captions blocks, no tiny font, no fake or gibberish words.**
- Aim for **about 4–8 labels maximum**, each **1–4 words**, **large** legible sans-serif. If unsure, use **fewer words** and rely on **clear layout** to carry meaning.

**Invented content:**
- Single document only; **no invented** numbers, dates, statistics, or labels not supported by the excerpt.

Output contract (strict):
- Output ONLY the final DALL-E prompt text (no markdown, JSON, or meta commentary).

DALL-E prompt craft:
- Start with e.g. "A clear flat-vector educational diagram / study sheet that visually explains..."
- Describe the **chosen layout (flow / comparison / timeline / concept map)** and **which concepts from the material** appear as **named stages or nodes**.
- **~100–160 words** total. Explicitly ask for **no decorative maze lines**, **no random symbols**, **readable large labels only**, **light background**, **limited palette** (e.g. 3–5 colors).

{% if retrieval_queries_note and retrieval_queries_note.strip() %}
Retrieval scope (stay aligned with the excerpt; do not add topics outside it):
{{ retrieval_queries_note }}

{% endif %}
{% if context and context.strip() %}
Source content (single document — visualize the **main thread** students must remember, using the formats above):
{{ context }}
{% else %}
No source excerpt. Ask for a single very simple neutral study diagram with almost no text and no specific factual claims.
{% endif %}

{% if custom_instructions %}
Additional user instructions (still keep one clear diagram type and no clutter):
{{ custom_instructions }}
{% endif %}

Final reminder: output ONLY the DALL-E prompt text.
```
