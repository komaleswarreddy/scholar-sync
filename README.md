# ScholarSync (NotebookLM for Schools)

Enterprise-grade AI Notebook platform for educational institutions with multi-tenancy support.

## Architecture

This is a **monorepo** that combines:

- **Turborepo** — orchestrates frontend (and any workspace) scripts
- **pnpm** — Node workspaces under `apps/*` and `packages/*`
- **Python 3.11+** — FastAPI API, shared library, Alembic migrations, and workers (Docker)

The backend is **not** a separate `backend/` folder. The HTTP app lives under **`apps/api`**, and domain logic, RAG, prompts, and DB migrations live under **`packages/core`**. Run Python commands from the **repository root** so imports resolve (`apps.api…`, `packages.core…`, `config…`).

### Structure

```
/
├── apps/
│   ├── api/                 # FastAPI app (routes, middleware) — entry: apps.api.main:app
│   └── web/                 # Next.js 14 (App Router) — package @scholarsync/web
├── packages/
│   ├── core/                # Python: services, RAG, LangGraph chat, prompts (.j2), DB models/migrations
│   └── types/               # Shared TypeScript types (Zod) — package @scholarsync/types
├── config/                  # Python settings (e.g. settings.py), YAML configs
├── docs/                    # Setup guides, API notes, used_prompts mirror, etc.
├── scripts/                 # start_backend.sh, seed_db.py (dev tenant)
├── tests/                   # pytest (unit / integration / load)
├── alembic.ini              # Migrations → packages/core/database/migrations
├── docker-compose.yml       # postgres, redis, api, worker
├── Dockerfile.api
├── Dockerfile.worker
├── pyproject.toml           # Python package metadata (scholarsync) + tool config
├── requirements.txt         # Python dependencies (primary install list)
├── package.json             # Turborepo root (pnpm)
├── pnpm-workspace.yaml
└── turbo.json
```

## Getting started

### Prerequisites

- **Node.js** 18+
- **pnpm** 8+ (repo pins `packageManager` in root `package.json`)
- **Python** 3.11+
- **PostgreSQL** 15+ (local or managed; Docker Compose provides a dev database)
- **Redis** — used by the optional Celery **worker** service in Docker
- **Pinecone** — vector index for RAG
- **Object storage** — AWS S3 and/or **Supabase** (see `.env.example`)
- **Clerk** — authentication for the web app
- **LLM providers** — OpenAI and/or Google Gemini (keys in `.env`)

### Installation

1. **Clone the repo** and open a terminal at the **monorepo root** (the folder that contains `package.json` and `requirements.txt`).

2. **JavaScript / frontend dependencies**

   ```bash
   pnpm install
   ```

3. **Python environment** (recommended: virtualenv at repo root)

   ```bash
   python -m venv venv
   # Windows: venv\Scripts\activate
   # macOS/Linux: source venv/bin/activate

   pip install --upgrade pip
   pip install -r requirements.txt
   ```

   Optional dev tools (from `pyproject.toml`): `pip install -e ".[dev]"`

4. **Environment variables**

   The API and workers read **`DATABASE_URL` and secrets from the repo root**. Next.js reads **`NEXT_PUBLIC_*` (and Clerk server keys) from the web app directory**. Use two files so local dev matches that split.

   **`/.env` (repository root — Python / FastAPI / scripts)**  
   - Copy **`.env.example`** → **`.env`** at the monorepo root (same folder as `alembic.ini`).  
   - Required for the API, Alembic, `scripts/seed_db.py`, and Docker Compose: `DATABASE_URL`, Clerk JWT verification keys, Pinecone, storage, LLM keys, `CORS_ORIGINS`, etc.  
   - Full key-by-key guide: [`docs/API_KEYS_EXPLAINED.md`](docs/API_KEYS_EXPLAINED.md)
   - If your DB password contains special characters (common ones: `@`, `#`, `$`, `:`), **URL-encode** them in `DATABASE_URL` (example: `$` → `%24`, `@` → `%40`). Otherwise you may see `password authentication failed` even when the password is correct.

   **`apps/web/.env.local` (Next.js — not committed)**  
   - Create **`apps/web/.env.local`** for variables that must be available in the browser or to the Next.js dev server.  
   - Typical entries:
     - **`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`** — Clerk publishable key (`pk_test_…` / `pk_live_…`). Required for sign-in UI.
     - **`NEXT_PUBLIC_API_URL`** — Optional. Base URL of the FastAPI server the browser calls (defaults to `http://localhost:8000` in code if unset). Set this if the API runs on another host or port.
     - **`CLERK_SECRET_KEY`** — Often set here as well for Clerk’s Next.js server middleware (same value as in root `.env`; see [Clerk Next.js env vars](https://clerk.com/docs/quickstarts/nextjs)).  
   - Next.js loads `.env.local` automatically when you run `pnpm dev` from the workspace; you do **not** need to copy the whole root `.env` into `apps/web/`.

5. **Database migrations** (from repo root, with venv activated)

   ```bash
   alembic upgrade head
   ```

6. **Database seed (development tenant)** — **after** migrations, **once per empty database** (or whenever you need the default dev tenant)

   The script [`scripts/seed_db.py`](scripts/seed_db.py) inserts a **single tenant** used for local development when you use `localhost` (middleware maps that host to tenant subdomain `default`):

   | Field | Value |
   |--------|--------|
   | `subdomain` | `default` |
   | `name` | `Development School` |
   | `id` | Fixed UUID `eeff7c1c-fe22-4573-ad93-a36f19ad4dc5` (so local data and docs stay consistent) |

   **When to run**

   - Right after **`alembic upgrade head`** on a **new** Postgres database (first clone, wiped volume, new machine).  
   - **Not** required before every `pnpm dev`; it is **idempotent** — if `default` already exists, the script prints that and exits.  
   - **Do not** rely on this for production tenant creation; use your normal provisioning flow there.

   **How to run** (repo root, virtualenv activated, root `.env` with valid `DATABASE_URL`):

   ```bash
   python scripts/seed_db.py
   # (or) python -m scripts.seed_db
   ```

   On Windows, use the same command after `venv\Scripts\activate`.

### Supabase quick schema setup (minimal)

If you are using **Supabase**, you have two supported ways to create tables:

#### Option A (recommended): Alembic migrations

Run this from the repo root (with venv active and `DATABASE_URL` set):

```bash
alembic upgrade head
python scripts/seed_db.py
```

**Supabase security baseline (important)**  
This repo assumes **all database access goes through the FastAPI backend** (Clerk-authenticated), not Supabase PostgREST from the browser. To prevent accidental data exposure via the Supabase Data API, the Alembic migrations also apply a security baseline on Supabase:

- Enable **Row Level Security (RLS)** on all app tables in `public`
- **Revoke** all table privileges from `anon` and `authenticated`
- Remove **default privileges** so future tables don’t auto-grant to those roles

In Supabase Security Advisor this may show as **Info**: “RLS enabled, no policy”. That is expected for a backend-only architecture.

#### Option B (quick start): Run a single SQL file in Supabase

Use this if you prefer setting up tables directly in the Supabase UI (or if you want a single copy/paste script):

1. Supabase dashboard → **SQL Editor** → run:
   - `scripts/supabase_schema.sql`

2. **Apply the Supabase security baseline** (required). After running the schema SQL, also run:
   - Enable RLS + FORCE RLS on the tables you created
   - Revoke privileges from `anon` and `authenticated`
   - Alter default privileges in `public` to revoke future grants

2. Then mark Alembic as applied (so future `alembic upgrade head` doesn't try to recreate tables):

   ```bash
   alembic stamp head
   ```

3. Then run the seed (safe to run even if the SQL inserted `default`):

   ```bash
   python scripts/seed_db.py
   # (or) python -m scripts.seed_db
   ```

### Running locally

**Important:** Start the API from the **repository root** so Python can import `apps` and `packages`.

- **FastAPI (development)**

  ```bash
  python -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
  ```

  - Interactive docs (development): `http://localhost:8000/api/docs`
  - Or use: `bash scripts/start_backend.sh` (activates `venv` / `.venv` if present)

- **Next.js web app**

  ```bash
  pnpm dev
  ```

  Runs Turborepo `dev` (currently the workspace app that defines `dev` is **`@scholarsync/web`**).  
  Equivalent: `pnpm --filter @scholarsync/web dev`  
  Default URL: `http://localhost:3000`

  **ChunkLoadError / `_next/static/chunks/...` timeout in dev:** Usually a **stale `.next` cache** or **two `next dev` processes** (one still on port 3000, another on 3001). Stop every dev server, then from repo root run `pnpm dev:web:clean` (clears `apps/web/.next` and starts Next), or manually delete `apps/web/.next` and run `pnpm dev` once. Open the URL printed in the terminal (3000 or 3001) and hard-refresh the browser.

- **Docker (API + Postgres + Redis + worker)**

  ```bash
  docker compose up
  ```

  Or only infrastructure + API: `docker compose up postgres redis api`  
  Ensure `.env` is present for API keys and secrets.

## Features

### Core

- **Multi-tenancy** — Subdomain-based tenant isolation
- **Sources** — PDFs, text, and web links; ingestion and retrieval
- **RAG chat** — Context-aware chat with routing, retrieval, and citations
- **Studio** — Quizzes, flashcards, mind maps, reports, slide decks, infographics
- **Notes** — Study notes tied to the workspace

### Tech stack (high level)

**Frontend (`apps/web`):** Next.js 14, Tailwind CSS, Zustand, TanStack Query, Clerk, React Markdown

**Backend:** FastAPI, SQLAlchemy (async), Alembic, Pinecone, LangGraph (chat orchestration), LlamaIndex-related adapters, OpenAI / Gemini (and optional Cohere for reranking per config)

## Multi-tenancy

Each school can use a dedicated subdomain, for example:

- `lincoln.scholarsync.com` → tenant `lincoln`
- `greenwood.scholarsync.com` → tenant `greenwood`

Isolation applies to database rows (`tenant_id`), Pinecone namespaces, and storage paths.

On **`localhost`**, the web middleware treats the tenant as **`default`** — that row is what `scripts/seed_db.py` creates for local development.

## Documentation

- **Environment / API keys:** [`docs/API_KEYS_EXPLAINED.md`](docs/API_KEYS_EXPLAINED.md)
- **Python setup (troubleshooting, versions):** [`docs/PYTHON_SETUP_GUIDE.md`](docs/PYTHON_SETUP_GUIDE.md)
- **Prompt templates (mirror of `packages/core/prompts/templates`):** [`docs/used_prompts/README.md`](docs/used_prompts/README.md)
- **Product / engineering specs** (repo root or `docs/`): e.g. `1_Product_Requirements_Document.md`, `4_API_Specification.md`, and related files

## Development

Run these from the **monorepo root** unless noted.

### Repo-wide (Node)

```bash
pnpm dev          # Turborepo dev (Next.js app)
pnpm build        # Production build(s)
pnpm lint         # ESLint via Turbo
pnpm type-check   # TypeScript check
pnpm clean        # Turbo clean
```

Build shared types package when you change it:

```bash
pnpm --filter @scholarsync/types build
```

### Python / API

```bash
# API (reload)
python -m uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# Tests
pytest

# Format / lint (if dev extras installed)
ruff check .
black .
```

After model changes, create or apply migrations:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

New or wiped database? Ensure the dev tenant exists (see **Database seed** in Getting started):

```bash
python scripts/seed_db.py
```

### Health check

```bash
curl http://localhost:8000/health
```

## License

Private - All Rights Reserved
