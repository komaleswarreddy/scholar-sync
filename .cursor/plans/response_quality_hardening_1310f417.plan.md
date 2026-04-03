---
name: Response quality hardening
overview: Add a structured teaching output template to RAG responses and reduce hallucinations without a full multi-pass pipeline by strengthening evidence-first prompting plus lightweight post-generation validation + conditional retry.
todos:
  - id: prompt-structured-template
    content: Update `packages/core/prompts/templates/chat/rag_prompt.j2` to enforce structured tutor-style sections for RAG responses, with intent-aware formatting and clear evidence-vs-general-knowledge rules.
    status: completed
  - id: hallucination-guard-validator
    content: Add deterministic hallucination guard module to score sentence support against retrieved context and flag unsupported claims.
    status: completed
  - id: conditional-retry
    content: Wire hallucination guard + one conditional retry into `packages/core/langgraph/chat_graph.py` before ModerationOutput; add feature flags and metrics/trace fields.
    status: completed
  - id: tests-hallucination-template
    content: Add unit tests for validator + retry trigger and a minimal prompt structure sanity test.
    status: completed
  - id: rollout-flags-metrics
    content: Add settings defaults (off), tracing hooks, and short staging rollout checklist.
    status: completed
isProject: false
---

# Response quality improvement plan (no multi-pass)

## Goals

- **Structured Teaching Output Templates**: enforce a tutor-style, skimmable structure in RAG answers.
- **Reduce hallucination**: make it hard to introduce unsupported facts, without adding a constant second LLM pass.

Scope decisions (from you):

- Apply templates **only when `context` exists** (RAG responses).
- Allow **limited general knowledge** when sources don’t cover it, but **clearly label** it as general (not from sources).

---

## Current baseline (what we have)

- Prompt already enforces grounding and has an exact refusal line in `[packages/core/prompts/templates/chat/rag_prompt.j2](packages/core/prompts/templates/chat/rag_prompt.j2)`.
- The graph already computes a confidence score post-output in `[packages/core/langgraph/chat_graph.py](packages/core/langgraph/chat_graph.py)` using `[packages/core/evaluation/confidence_scorer.py](packages/core/evaluation/confidence_scorer.py)`.

---

## Phase A — Structured teaching template in `rag_prompt.j2`

### A1. Add a strict response skeleton (RAG-only)

Update `[packages/core/prompts/templates/chat/rag_prompt.j2](packages/core/prompts/templates/chat/rag_prompt.j2)` in the `if context` branch to require these sections for most intents:

- `## From your documents` (2–6 bullets)
  - Each bullet must be supported by the context evidence.
- `## Simple explanation` (plain language, 4–8 lines)
- `## Real-life example` (1 concrete scenario)
- `## Related concepts` (3–5 short bullets)
- `## Summary` (2–3 lines)

Intent-aware adjustments (minimal):

- `definition` / short factual: allow a shorter structure (answer + `## From your documents` + `## Summary`).
- `comparison`: add `## Similarities` / `## Differences` subsections.
- `how_to`: require numbered steps.

### A2. Tighten “evidence vs general knowledge” rules

Add explicit language:

- **Supported**: claims directly grounded in `Context evidence`.
- **General knowledge**: allowed only when context is missing details; must be labeled with a prefix like `General knowledge:` and must not contradict the context.
- If nothing relevant exists: keep current exact refusal **unless** user asked a general question not about their materials.

---

## Phase B — Hallucination reduction (single-pass + conditional retry)

### B1. Evidence-first prompting

In the same prompt file:

- Require the model to “quote-check” itself: before stating a specific fact (dates, numbers, definitions, named entities), ensure it appears in the context; otherwise label as general knowledge or omit.
- For multi-claim answers: prefer extracting key points first (“From your documents” bullets) then explain—still **single generation**.

### B2. Lightweight post-generation validator (no second LLM)

Add a deterministic validator that runs after generation (before moderation output), e.g. new module:

- `[packages/core/rag/hallucination_guard.py](packages/core/rag/hallucination_guard.py)`

It will:

- Split answer into sentences.
- Ignore sentences under a small length threshold.
- Mark sentences as “needs support” if they contain high-risk patterns:
  - numbers/years, quoted strings, strong assertions (`is`, `causes`, `results in`), named entities heuristic.
- For “needs support” sentences, check whether there is sufficient lexical overlap with the retrieved `context` (or the chunk texts). Use a simple token overlap / BM25-like score (no embeddings).

Outputs:

- `supported_ratio` and list of `unsupported_sentences`.

### B3. Conditional retry (only when risky)

If `supported_ratio` is below a threshold (e.g. 0.65) **and** context exists:

- Re-run generation **once** with a stricter instruction string appended (still not a full multi-pass design; it’s a targeted retry).
- The stricter instruction: “Remove or label any claim not directly supported by Context evidence; prefer quoting phrases; if still unsupported, say what is missing.”

Add feature flags (default off until staging validated):

- `ENABLE_HALLUCINATION_GUARD`
- `HALLUCINATION_GUARD_MIN_SUPPORTED_RATIO`
- `HALLUCINATION_GUARD_MAX_RETRY` (default 1)

Wire point: inside the `Generate` node or immediately after it in `[packages/core/langgraph/chat_graph.py](packages/core/langgraph/chat_graph.py)` before `ModerationOutput`.

---

## Phase C — Tests

Add unit tests around the new validator:

- Supported sentence passes when present in context.
- Numeric fact not in context is flagged.
- General-knowledge labeled sentences are excluded from “must support” set.
- Retry triggers only when thresholds fail.

Likely paths:

- `tests/unit/test_hallucination_guard.py`
- Prompt snapshot sanity checks (minimal) for `rag_prompt.j2` sections.

---

## Phase D — Rollout

- Ship with flags **off** in production.
- Enable in staging with a small percentage or internal users.
- Watch:
  - latency impact (retry rate)
  - `supported_ratio` distribution
  - user feedback on “General knowledge” labeling clarity

---

## Notes (why this is not “multi-pass”)

- There is **one** answer generation pass by default.
- Only **conditional** single retry happens when the deterministic validator indicates high hallucination risk.
- No separate “fact extraction pass” LLM call is added to every request.

