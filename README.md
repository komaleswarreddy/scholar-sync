# ScholarSync (NotebookLM for Schools)

Enterprise-grade AI Notebook platform for educational institutions with multi-tenancy support.

## 🏗️ Architecture

This is a **monorepo** built with:
- **Turborepo** for build orchestration
- **pnpm** for package management
- **TypeScript** for type safety

### Structure

```
/
├── apps/
│   ├── web/              # Next.js 14 Web App
│   └── mobile/           # React Native/Expo App (coming soon)
├── packages/
│   ├── types/            # Shared TypeScript types
│   └── api/              # Shared API client
└── backend/              # FastAPI Python backend
```

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- pnpm 8+
- Python 3.11+
- PostgreSQL 15+
- Pinecone account
- AWS S3 bucket (or Supabase Storage)
- Clerk account for authentication

### Installation

1. **Install dependencies:**
   ```bash
   pnpm install
   ```

2. **Set up environment variables:**
   - Copy `.env.example` files in each directory
   - Fill in your API keys and configuration

3. **Set up database:**
   ```bash
   cd backend
   # Run migrations (Alembic)
   alembic upgrade head
   ```

4. **Start development servers:**
   ```bash
   # Start all apps
   pnpm dev
   
   # Or start individually:
   pnpm --filter @scholarsync/web dev
   pnpm --filter backend dev
   ```

## 📚 Features

### Core Features
- ✅ **Multi-Tenancy**: Subdomain-based tenant isolation
- ✅ **Source Management**: Upload PDFs, text, and web links
- ✅ **RAG Chat**: Context-aware chat with citations
- ✅ **Studio Suite**: Generate quizzes, flashcards, mind maps, reports, etc.
- ✅ **Notes**: Save and organize study notes

### Tech Stack

**Frontend:**
- Next.js 14 (App Router)
- Tailwind CSS
- Zustand (State Management)
- TanStack Query (Data Fetching)
- Clerk (Authentication)

**Backend:**
- FastAPI (Python)
- SQLAlchemy (Async ORM)
- Pinecone (Vector DB)
- AWS S3 (Storage)
- Gemini 1.5 Flash & GPT-4o-mini (LLMs)

## 🔐 Multi-Tenancy

Each school gets a unique subdomain:
- `lincoln.scholarsync.com` → Tenant: "lincoln"
- `greenwood.scholarsync.com` → Tenant: "greenwood"

Data is isolated at:
- **Database**: Row-level security with tenant_id
- **Vector DB**: Namespace-based isolation in Pinecone
- **Storage**: Tenant-scoped S3 paths

## 📖 Documentation

### Core Documentation
- `1_Product_Requirements_Document.md` - Product requirements
- `2_Functional_Technical_Requirements.md` - Functional specs
- `3_Tech_Stack_Architecture.md` - Architecture overview
- `4_API_Specification.md` - API documentation
- `5_Design_Specifications.md` - Design guidelines
- `6_Coding_Standards_Best_Practices.md` - Coding standards

### Setup Guides
- `API_KEYS_EXPLAINED.md` - Complete guide to setting up all required API keys and services

## 🛠️ Development

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd apps/web
pnpm dev
```

## 📝 License

Private - All Rights Reserved
