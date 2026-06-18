# Prompt & Model Optimization — Tiered Evaluation Datasets

Golden datasets for **prompt tuning, regression evals, and LangSmith** upload.  
Sourced from `tests/Prompt_and_Model_Optimization_Tiered_Dataset_Plan.xlsm`.

## Layout

```
prompt_tiered/
  manifest.json          # Index of all agent datasets
  schema.json            # Shared item schema
  routing/               # Intent classifier
  retrieval/             # Query rewriter, decomposer, scope narrower
  generation/            # Chat policy, direct chat, summarizer, hallucination guard
  studio/                # Quiz, flashcards, mind map, slide deck, legacy
  problem_solving/       # DNA analyzer + coach modes
  tutor_mode/            # Bootstrap + follow-ups
  source_upload/         # Ingestion, OCR, map/reduce
  safety/                # Refusal template routing
```

**Excluded:** `generation/rag_chat_response_generator` — covered separately / existing RAG golden sets.

## Item format (LangSmith-compatible)

Each file is JSON with:

| Field | Purpose |
|-------|---------|
| `inputs` | Variables passed to the Jinja prompt template |
| `reference_outputs` | Expected JSON, text, or judge criteria |
| `variation` | Industry eval axis (typo, diagram, numerical, security, …) |
| `tags` | Board/subject/tier filters |
| `evaluators` | Suggested automated checks |

## Tier sizes

| Tier | Examples per agent | Use |
|------|-------------------|-----|
| Tier 1 | 30 | High-traffic routing / generation |
| Tier 2 | 15 | Studio, summarization, OCR |
| Tier 3 | 5 | Optional / legacy / policy smoke |

## Regenerate

```powershell
python scripts/generate_prompt_tiered_datasets.py
```

## Upload to LangSmith (optional)

```powershell
# After LANGSMITH_API_KEY is set in .env
python scripts/upload_prompt_tiered_to_langsmith.py --agent intent_classifier
```
