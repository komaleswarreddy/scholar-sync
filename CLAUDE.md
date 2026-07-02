# ScholarSync — Claude Code Guide

## Project Overview

**ScholarSync** is an enterprise-grade AI Notebook platform for educational institutions. It provides multi-tenant RAG-powered chat, AI-generated study materials (quizzes, flashcards, mind maps), a tutor mode (NCERT curriculum), and a problem-solving assistant.

Monorepo with Python backend (FastAPI + LangGraph) and Next.js 14 frontend.

---

## Architecture

```
NotebookLM/
├── apps/
│   ├── api/          # FastAPI backend
│   ├── web/          # Next.js 14 frontend (TypeScript)
│   └── worker/       # Celery async worker
├── packages/
│   ├── core/         # Python domain logic (RAG, LangGraph, services, DB, prompts)
│   └── types/        # Shared TypeScript types (Zod)
├── config/           # Python settings (settings.py, YAML configs)
├── docs/             # Setup guides, prompt templates
├── scripts/          # Seed DB, migrations, eval utilities
├── tests/            # pytest suite (unit, integration, load)
└── infrastructure/   # Deployment configs
```

---

## Tech Stack

### Backend (Python 3.11+)
- **FastAPI 0.109** — HTTP API
- **SQLAlchemy 2.0** + **asyncpg** — async ORM + PostgreSQL
- **Alembic 1.13** — DB migrations
- **LangGraph 0.2+** — chat orchestration state machine
- **LlamaIndex 0.13–0.15** — RAG indexing/retrieval
- **Pinecone 7+** — vector store (namespace-per-tenant isolation)
- **OpenAI 1.10+** / **Anthropic** / **Google Gemini** — LLM providers
- **Cohere 5+** — reranking
- **Celery 5.3+** + **Redis 7** — async task queue
- **Clerk** (python-jose) — JWT auth

### Frontend (Node 18+)
- **Next.js 14** App Router, TypeScript
- **TanStack Query 5** — server state
- **Zustand** — client state
- **Clerk** — auth UI
- **Tiptap** — rich text editor
- **D3** — mind map visualization
- **Zod** + **React Hook Form** — validation

### Infrastructure
- **PostgreSQL 15+**, **Redis 7**, **AWS S3 / Supabase Storage**
- **Docker Compose** (local dev), **Turborepo** (monorepo), **pnpm 8**

---

## Running Locally

### Prerequisites
- Python 3.11+, Node 18+, pnpm 8+
- PostgreSQL 15+, Redis (or use Docker Compose)
- API keys: OpenAI, Gemini/Anthropic, Clerk, Pinecone
- S3 or Supabase credentials

### Setup
```bash
# Install Node deps
pnpm install

# Python venv (from repo root)
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Environment
cp .env.example .env          # Fill in API keys, DATABASE_URL, etc.
cp apps/web/.env.example apps/web/.env.local

# DB setup
alembic upgrade head
python scripts/seed_db.py
```

### Development
```bash
# Terminal 1: API (http://localhost:8000)
python -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend (http://localhost:3000)
pnpm dev
```

### Docker (alternative)
```bash
docker compose up
```

### Makefile shortcuts
```bash
make dev-api      # Start API
make migrate      # Run Alembic migrations
make test         # pytest
make lint         # ruff + mypy
make format       # black + ruff --fix
```

---

## Key Files

| Area | Path |
|------|------|
| API entry point | `apps/api/main.py` |
| API routes | `apps/api/routes/` |
| Chat orchestration | `packages/core/langgraph/chat_graph.py` |
| Chat state schema | `packages/core/langgraph/chat_state.py` |
| RAG pipeline | `packages/core/rag/` |
| Services | `packages/core/services/` |
| DB models | `packages/core/database/models/` |
| DB connection | `packages/core/database/connection.py` |
| Prompt templates | `packages/core/prompts/templates/` |
| Config/settings | `config/settings.py` |
| Frontend app | `apps/web/src/app/` |
| Shared TS types | `packages/types/` |

---

## API Routes (`apps/api/routes/`)

| Route file | Purpose |
|------------|---------|
| `chat.py` | RAG chat via LangGraph |
| `sources.py` | PDF/text ingestion |
| `studio.py` | Quiz/flashcard/mind-map generation |
| `notes.py` | Note CRUD |
| `notebooks.py` | Workspace management |
| `tutor.py` | NCERT curriculum tutor mode |
| `problem_solver.py` | Step-by-step problem solving |
| `admin.py` | Tenant/user/guardrail admin |
| `metrics.py` | Cost, latency, token tracking |
| `health.py` | Health checks |

API docs: `http://localhost:8000/api/docs`

---

## Multi-Tenancy

- Subdomain-based routing (`lincoln.scholarsync.com`)
- Tenant middleware extracts tenant from host header
- Row-level filtering on all DB queries by `tenant_id`
- Pinecone namespace isolation per tenant

---

## RAG Pipeline (`packages/core/rag/`)

1. **Chunker** — semantic text splitting
2. **Embedder** — OpenAI embeddings
3. **Hybrid Retriever** — BM25 + Pinecone vector search fusion
4. **Context Grounding Gate** — relevance filtering
5. **Reranker** — Cohere reranking
6. **Hallucination Guard** — output fact-checking

---

## Testing

```bash
pytest                            # All tests
pytest tests/unit/               # Unit only
pytest tests/integration/        # Integration (requires INTEGRATION_TESTS=1)
pytest -m retrieval              # By marker
pytest --cov=packages/core --cov=apps/api --cov-report=html
```

Test markers: `integration`, `ingestion`, `retrieval`, `notebook_mode`, `studio`, `guardrails`, `slow`, `load`

---

## Environment Variables

- **Root `.env`**: `DATABASE_URL`, `OPENAI_API_KEY`, `PINECONE_API_KEY`, `CLERK_SECRET_KEY`, `SUPABASE_*` / `AWS_*`, `REDIS_URL`, `LANGSMITH_*`
- **`apps/web/.env.local`**: `NEXT_PUBLIC_CLERK_*`, `NEXT_PUBLIC_API_URL`

---

## Current Branch

`authentication_userflow` — auth-related changes in progress.

---

## LangSmith Eval System — Full Context

> **Complete workspace/agent status:** `docs/LANGSMITH_EVAL_STATUS.md`  
> **Ground truth for runs:** `Reference dataset/testing_Results.csv`  
> **Switch accounts:** `python scripts/switch_workspace.py <label>`

### Architecture Overview

The eval system lives in `evals/` and runs a **prompt × model × agent bake-off** across 27 agents, 3 prompt versions (v1/v2/v3), and 2-3 models per agent. All experiments are tracked in LangSmith.

**Key files:**
| File | Purpose |
|------|---------|
| `evals/agent_eval/run_matrix.py` | Main runner — `--step`, `--all`, `--status`, `--dry-run` |
| `evals/agent_eval/config.py` | Model skip flags, dataset naming, `ensure_langsmith_env()` |
| `evals/agent_eval/registry.py` | Agent→dataset→evaluator mapping, `AgentSpec` |
| `evals/agent_eval/evaluator_loader.py` | Dynamically loads per-agent evaluator modules |
| `evals/agent_eval/llm_judge.py` | GPT-4o LLM-as-judge for open-ended outputs |
| `evals/agent_eval/rate_limit_guard.py` | Local ledger; aborts if monthly trace cap would be hit |
| `evals/agent_eval/agent_models.json` | Per-agent model matrix (source of truth for which models run) |
| `evals/agent_eval/prompt_versions/` | v1/v2/v3 system + user prompt templates per agent |
| `evals/datasets/prompt_tiered/` | JSON datasets (manifest.json = index of all 27 agents) |
| `evals/datasets/final_Evalutors/` | One evaluator `.py` per agent with `PER_EXAMPLE_EVALUATORS` + `SUMMARY_EVALUATORS` |
| `evals/intent_classifier_eval/run_eval.py` | Separate harness for intent_classifier only |
| `evals/reports/agent_matrix/` | Leaderboard JSON + trace ledger + step checkpoint |
| `Reference dataset/testing_Results.csv` | Ground truth: which agents/models/workspaces are done |

### How to Run

```bash
# Check progress
python -m evals.agent_eval.run_matrix --status

# Run ONE experiment then pause (recommended — respects trace limit)
python -m evals.agent_eval.run_matrix --step

# Run specific agent only
python -m evals.agent_eval.run_matrix --step --agent problem_dna_analyzer

# Run all pending sequentially (checkpointed, safe to interrupt)
python -m evals.agent_eval.run_matrix --all

# Dry-run (shows plan without executing)
python -m evals.agent_eval.run_matrix --dry-run

# Intent classifier (separate harness)
python -m evals.intent_classifier_eval.run_eval --step
```

### Multi-Account LangSmith Setup (CRITICAL)

**No MCP needed.** The harness reads `LANGSMITH_API_KEY` from `.env`. To switch accounts, just change that key. The `rate_limit_guard.py` uses a **local** ledger (`evals/reports/agent_matrix/trace_ledger.json`) to track traces — one ledger per workspace is needed when switching.

**Why multiple accounts:** LangSmith free tier = 5,000 traces/month. With ~3 models × 3 prompts × N examples per agent, one account runs out fast. Each Gmail account is a separate LangSmith workspace.

**Account → Tenant → Agents mapping (10 workspaces total):**

| Label | Gmail | Tenant ID | Agents | Budget |
|-------|-------|-----------|--------|--------|
| `pscmrmindssprint2k25` | pscmrmindssprint2k25@gmail.com | `15d476d5` | intent_classifier | **EXHAUSTED** |
| `scombinator26` | scombinator26@gmail.com | `47ca8a69` | query_rewriter, query_decomposer, scope_narrower | **EXHAUSTED** |
| `emaildam3` | emaildam3@gmail.com | `aafff4b5` | direct_chat, chat_summarizer, rag_chat_response_generator | Available |
| `gra7399` | gra7399@gmail.com | `67272628` | studio_system_json, studio_quiz | Available |
| `sui332307` | sui332307@gmail.com | `33d88f33` | studio_flashcards, studio_mind_map, studio_slide_deck | Available |
| `eskomal66` | eskomal66@gmail.com | `03ba6fa5` | studio_fallback_legacy | Available |
| `cursemes9` | cursemes9@gmail.com | `ac6f370c` | agents 15–27 (fresh runs per SOP) | Available |
| `sujithgundala97` | sujith.gundala97@gmail.com | `bf982111` | old partial runs (not relied upon) | Do not use |
| `kumarsujith006` | kumarsujith006@gmail.com | `3ee9feb1` | old partial runs (not relied upon) | Do not use |
| `citizena45` | citizena45@gmail.com | `9fced417` | agents 14–16 (fresh runs) | **ACTIVE** — 3672/4750 used (1078 remaining) |

**To switch to a different account before running:**
```bash
# In .env — swap to the target account's API key
LANGSMITH_API_KEY=lsv2_pt_XXXX...   # get from smith.langchain.com → Settings → API Keys
LANGSMITH_PROJECT=ScholarSync
```

The datasets (`nbm-prompt-{agent_id}`) must already exist in that workspace. The harness does NOT auto-create datasets — they must be uploaded first via LangSmith UI or SDK.

### Agent Completion Status (as of 2026-07-02)

**DONE (13 agents — all 3 prompts, all runtime models):**
1. intent_classifier ✅
2. query_rewriter ✅ (Gemini skipped — health-check fail)
3. query_decomposer ✅ (Gemini skipped)
4. scope_narrower ✅ (Gemini skipped)
5. direct_chat ✅ (Gemini skipped)
6. chat_summarizer ✅ (Gemini skipped)
7. rag_chat_response_generator ✅
8. studio_system_json ✅
9. studio_quiz ✅ (Gemini skipped)
10. studio_flashcards ✅ (Gemini skipped)
11. studio_mind_map ✅
12. studio_slide_deck ✅
13. studio_fallback_legacy ✅

**REMAINING (14 agents — strict SOP, fresh run per agent, do NOT rely on old partial runs):**

| # | Agent ID | Fresh Workspace | SOP Status |
|---|----------|-----------------|------------|
| 14 | problem_dna_analyzer | shivaprapul550 + shivaprapulsp | ✅ DONE — 9/9 combos complete. gpt-5.4-mini + gpt-5.4 × v1/v2/v3 on shivaprapul550 (dataset `6b934edf`); claude-sonnet-4-6 × v1/v2/v3 + gpt-5.4-mini/gpt-5.4 × v3 rerun on shivaprapulsp (dataset `0ec56467`) after Anthropic limit fixed. All outputs OK. |
| 15 | whole_file_reduce | shivaprapul550 | ✅ DONE — 9/9 combos complete (gpt-5.4, gemini-2.5-flash, gpt-5-mini × v1/v2/v3). All outputs OK. Dataset `4c9ac445`. |
| 16 | whole_file_map_summarizer | shivaprapul550 | ✅ DONE — 9/9 combos complete (gpt-5.4-mini, gemini-3.1-flash-lite, gpt-5-nano × v1/v2/v3). All outputs OK. Dataset `3f5e8566`. |
| 17 | explain_from_basics | shivaprapul550 + shivaprapulsp | ✅ DONE — 9/9 combos complete. v1/gpt-5.4 + v1/gemini + v2/gpt-5.4 on shivaprapul550 (dataset `991db143`); claude reruns (v1+v2) + v2/gemini + all v3 on shivaprapulsp (dataset `9268ee47`). Gemini healthy. All outputs OK. |
| 18 | show_best_approach | cursemes9 | ⏳ Not started |
| 19 | show_missing_idea | cursemes9 | ⏳ Not started |
| 20 | ncert_document_sketch | cursemes9 | ⏳ Not started |
| 21 | help_me_solve_it | cursemes9 | ⏳ Not started |
| 22 | problem_solver_followup | cursemes9 | ⏳ Not started |
| 23 | tutor_notebook_bootstrap | cursemes9 | ⏳ Not started |
| 24 | tutor_follow_up_questions | cursemes9 | ⏳ Not started |
| 25 | source_question_extraction | cursemes9 | ⏳ Not started |
| 26 | image_ocr | cursemes9 | ⏳ Not started |
| 27 | diagram_label_ocr | cursemes9 | ⏳ Not started |

**Gemini status across all agents:** All Gemini models are configured with `skip_runtime=false` in `agent_models.json` — harness runs a health check at runtime and auto-skips if 503/UNAVAILABLE. Agents 15 and 16 confirmed Gemini healthy and ran successfully. Always attempt Gemini; the harness decides at runtime.

### Evaluator Structure

Each agent has exactly one evaluator file in `evals/datasets/final_Evalutors/`:
- `PER_EXAMPLE_EVALUATORS` — list of `fn(run, example) → {key, score, comment}` functions
- `SUMMARY_EVALUATORS` — list of `fn(runs, examples) → {key, score, comment, ship_recommendation}` functions
- `parse_model_response_to_outputs(raw_text) → dict` — parses LLM output into output keys
- Agents in `AGENTS_REQUIRING_JUDGE` frozenset use `build_per_example_evaluators(judge_llm)` instead

Judge model is always `gpt-4o` (OpenAI). Never changed to Gemini/Claude for judging.

### Dataset naming convention
LangSmith dataset name = `nbm-prompt-{agent_id}` (e.g. `nbm-prompt-intent_classifier`)

### Trace budget math (free tier)
- 5,000 traces/month per workspace
- Safety margin: 250 traces reserved
- Usable: 4,750 traces/month
- Each experiment = N_examples (target traces) + N_examples × N_per_eval_evaluators + N_summary_evaluators (evaluator traces)
- Ledger file: `evals/reports/agent_matrix/trace_ledger.json` — must be reset or checked when switching workspaces

---

## Strict Agent Eval SOP — One-by-One Process

> **This is the mandatory process for every remaining agent (14–27). No shortcuts. Do not skip any step. Do not rely on old/partial runs from sujithgundala97 or kumarsujith006.**

### Process (repeat exactly for each agent in order)

**STEP 1 — Analyze the evaluator for bugs**
- Read the evaluator file: `evals/datasets/final_Evalutors/{agent_id}_evaluators.py`
- Read the agent's dataset JSON: `evals/datasets/prompt_tiered/**/{agent_id}.json`
- Read the agent's prompt templates: `evals/agent_eval/prompt_versions/{agent_id}/v1.json`, `v2.json`, `v3.json`
- Cross-check every constant, set, band, type, regex against actual data values in the dataset
- Known bug categories to check for every agent:
  - `parse_model_response_to_outputs` — does it handle dict output, code-fenced JSON, extra fields?
  - Hard-coded sets (valid types, valid labels, etc.) — do they match what the prompt actually instructs the model to produce?
  - Numeric bands/ranges — do they match the gold-answer values in the dataset?
  - Judge-failure handling — does a 429/SSL error set `hard_rule_violated=True`? (must be False)
  - Schema validity check — uses strict equality instead of subset check?
  - MAX_TOKENS_BY_AGENT — is the agent listed? Is the value large enough for its expected output JSON?
- Write a detailed bug report listing every issue found (key, what's wrong, evidence from dataset)

**STEP 2 — Apply all fixes**
- Fix every bug found in Step 1
- Do NOT change logic beyond what the bug requires
- Do NOT refactor or clean up unrelated code

**STEP 3 — Verify 100% (sanity check — mandatory)**
- For every fix applied: grep/read the file to confirm the exact new code is present
- For MAX_TOKENS_BY_AGENT: grep `run_matrix.py` for the agent_id to confirm the entry exists
- For set/band changes: confirm new values match dataset gold answers exactly
- Print a verification table: Fix # | What was fixed | Verified (Y/N) | Evidence
- Do NOT proceed to Step 3.5 until all fixes are verified ✅

**STEP 3.5 — Credit check (mandatory before every run)**
```bash
python scripts/check_api_credits.py --agent {agent_id}
```
- Exit 0 = all required providers OK → safe to proceed
- Exit 1 = hard failure (quota/auth) → STOP, notify user, do NOT run eval
- Gemini WARN (503/unavailable) = soft fail → harness auto-skips at runtime, proceed
- Anthropic monthly limit resets 2026-08-01; OpenAI and Gemini unaffected

**STEP 4 — Prepare fresh workspace**
- Assign the agent to its fresh workspace (see table above)
- Switch `.env` to that workspace's API key: `python scripts/switch_workspace.py {label}`
- This automatically archives the old ledger and resets the trace budget to 0

**STEP 5 — Clear stale checkpoint entries**
- Remove any old checkpoint entries for this agent from `evals/reports/agent_matrix/step_checkpoint.json`
  ```python
  import json; p = "evals/reports/agent_matrix/step_checkpoint.json"
  ck = json.load(open(p)); ck2 = {k:v for k,v in ck.items() if "{agent_id}" not in k}
  json.dump(ck2, open(p,"w"), indent=2)
  ```

**STEP 6 — Upload dataset to fresh workspace**

> ⛔ CRITICAL SAFETY RULE — READ BEFORE EVERY UPLOAD:
> **NEVER use `--force` or any flag that deletes an existing dataset if experiments have already run against it.**
> Using `--force` on an existing dataset PERMANENTLY DELETES all experiment comparison data linked to that dataset.
> The traces still exist in the project view but are unrecoverable in dataset comparison format.
> This mistake caused agents 14/15/16 experiment data to be permanently lost.
>
> **Safe upload checklist (mandatory before running upload):**
> 1. Go to LangSmith → Datasets & Experiments in the target workspace
> 2. Search for `nbm-prompt-{agent_id}` — if it already exists, CHECK whether it has experiments
> 3. If it has experiments → DO NOT upload/overwrite → reuse the existing dataset, record its ID
> 4. If it does NOT exist OR is confirmed empty → safe to upload
> 5. NEVER upload ALL datasets at once — only upload the single target agent's dataset
> 6. NEVER use `upload_agent_eval_datasets.py` (uploads all) — always use `upload_prompt_tiered_to_langsmith.py --agent {agent_id}` (single agent)

- Upload ONLY if the dataset does not exist in the target workspace:
  ```python
  python scripts/upload_prompt_tiered_to_langsmith.py --agent {agent_id}
  ```
- Confirm dataset ID from the upload output — record it
- Navigate to LangSmith and verify the dataset exists with correct examples count before proceeding

**STEP 7 — Run the eval**
```bash
python -m evals.agent_eval.run_matrix --all --agent {agent_id}
```
- Run in background; monitor the log file
- Expected: 9 combos (v1/v2/v3 × {agent-specific models}); Gemini attempted — auto-skipped if unhealthy

**STEP 8 — Verify results in LangSmith**
- Navigate to the dataset in LangSmith → Experiments tab
- All experiments must show non-empty Outputs column
- All evaluator scores must be non-zero (not all 0.00)
- If any experiment has empty outputs → root-cause before proceeding
- Record the exact dataset ID and experiment session IDs from the URL

**STEP 9 — Update records**
- Update `Reference dataset/testing_Results.csv` — mark agent as complete with workspace, dataset ID, experiment links
- Update `CLAUDE.md` agent status table — change from ⏳ to ✅
- Update `docs/LANGSMITH_EVAL_STATUS.md`

**STEP 10 — Move to next agent**
- Only after Step 9 is complete, start Step 1 for the next agent

### Rule: Never run without completing Steps 1–3 first
> Every agent gets a full evaluator audit. Even if an evaluator looks clean, systematically verify all 5 bug categories from Step 1. An untested evaluator that produces all-zero scores wastes the entire trace budget.

### Rule: Never upload a dataset that already has experiments — EVER
> Uploading with --force or overwriting an existing dataset destroys all experiment comparison data permanently.
> Agents 14/15/16 lost all LangSmith dataset experiment data due to this mistake.
> Before any upload: check LangSmith UI first. If experiments exist → skip upload, reuse dataset.

---

## Import Conventions

```python
# Python — always from repo root
from apps.api.routes import chat
from packages.core.services import chat_service
from packages.core.rag import retriever
```

```typescript
// TypeScript workspace packages
import { NotebookSchema } from "@scholarsync/types"
```
