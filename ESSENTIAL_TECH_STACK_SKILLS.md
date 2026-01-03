# Essential Tech Stack Skills - Priority List
**Based on Current Implementation**

---

## 🔴 **TIER 1: CORE (MUST HAVE)**

### **Frontend (Web)**
1. **Next.js 14 (App Router)** ⭐⭐⭐
   - Server Components vs Client Components
   - Route handlers, middleware
   - File-based routing patterns
   - **Current:** `next@14.1.0`

2. **TypeScript 5.3+ (Strict Mode)** ⭐⭐⭐
   - Type safety across monorepo
   - Shared types package (`@scholarsync/types`)
   - **Current:** `typescript@5.3.3`

3. **React 18+** ⭐⭐⭐
   - Hooks (useState, useEffect, useCallback, useMemo)
   - Context API patterns
   - **Current:** `react@18.2.0`

4. **TanStack Query v5** ⭐⭐⭐
   - Server state management
   - Caching, refetching, error handling
   - **Current:** `@tanstack/react-query@5.17.0`

5. **Zustand** ⭐⭐
   - Global state management
   - **Current:** `zustand@4.4.7`

6. **Tailwind CSS** ⭐⭐⭐
   - Utility-first styling
   - Custom design tokens
   - **Current:** `tailwindcss@3.4.1`

7. **Zod** ⭐⭐
   - Runtime validation
   - Schema definitions
   - **Current:** `zod@3.22.4`

### **Backend (Python)**
1. **FastAPI** ⭐⭐⭐
   - Async/await patterns
   - Background tasks
   - Streaming responses (SSE)
   - **Current:** `fastapi@0.109.0`

2. **SQLAlchemy 2.0 (Async)** ⭐⭐⭐
   - Async ORM patterns
   - Database queries
   - **Current:** `sqlalchemy@2.0.25`

3. **Pydantic v2** ⭐⭐⭐
   - Data validation
   - Settings management
   - **Current:** `pydantic@2.5.3`

4. **Alembic** ⭐⭐
   - Database migrations
   - **Current:** `alembic@1.13.1`

### **AI/ML Integration**
1. **RAG Implementation** ⭐⭐⭐
   - Vector embeddings
   - Context retrieval
   - Chunking strategies

2. **OpenAI API** ⭐⭐⭐
   - Embeddings (`text-embedding-3-small`)
   - **Current:** `openai@1.10.0`

3. **Google Gemini API** ⭐⭐⭐
   - Chat responses (`gemini-2.5-flash`)
   - **Current:** `google-generativeai@0.3.2`

4. **Pinecone** ⭐⭐⭐
   - Vector database operations
   - Namespace management
   - **Current:** `pinecone-client@3.0.0`

### **Infrastructure**
1. **PostgreSQL (Supabase)** ⭐⭐⭐
   - Database operations
   - Row Level Security (RLS)
   - Multi-tenancy

2. **Supabase Storage** ⭐⭐
   - File uploads/downloads
   - **Current:** Using `supabase` Python client

---

## 🟡 **TIER 2: CRITICAL FOR ENTERPRISE**

### **Monorepo Management**
1. **Turborepo** ⭐⭐
   - Build orchestration
   - Caching strategies
   - **Current:** `turbo@2.0.0`

2. **pnpm Workspaces** ⭐⭐
   - Package management
   - **Current:** `pnpm@8.15.0`

### **UI Components**
1. **Radix UI** ⭐⭐
   - Headless components
   - Accessibility
   - **Current:** `@radix-ui/react-*`

2. **React Hook Form** ⭐
   - Form handling
   - **Current:** `react-hook-form@7.49.3`

### **Testing** (Not yet implemented - **MUST ADD**)
1. **Playwright** ⭐⭐⭐
   - E2E web testing
   - **Status:** ❌ Not configured

2. **Jest + React Testing Library** ⭐⭐⭐
   - Unit/integration tests
   - **Status:** ❌ Not configured

3. **pytest** ⭐⭐⭐
   - Backend testing
   - **Status:** ❌ Not configured

### **Deployment** (Not yet configured - **MUST ADD**)
1. **Vercel** ⭐⭐⭐
   - Next.js deployment
   - **Status:** ❌ Not configured

2. **Docker** ⭐⭐
   - Containerization
   - **Current:** Dockerfile exists

3. **CI/CD (GitHub Actions)** ⭐⭐⭐
   - Automated testing/deployment
   - **Status:** ❌ Not configured

### **Mobile** (Planned - **MUST ADD**)
1. **React Native + Expo SDK 50** ⭐⭐⭐
   - Cross-platform mobile
   - **Status:** ❌ Not implemented

2. **Expo Router** ⭐⭐
   - File-based routing
   - **Status:** ❌ Not implemented

---

## 🟢 **TIER 3: IMPORTANT FOR QUALITY**

### **Error Handling & Monitoring**
1. **Sentry** ⭐⭐
   - Error tracking
   - **Status:** ❌ Not configured

2. **Axios** ⭐
   - HTTP client
   - **Current:** `axios@1.6.5`

### **File Processing**
1. **pypdf** ⭐⭐
   - PDF text extraction
   - **Current:** `pypdf@4.0.1`

### **Authentication** (Partially configured)
1. **Clerk** ⭐⭐
   - User authentication
   - **Current:** `@clerk/nextjs@5.0.0` (bypassed in dev)

---

## 📊 **SKILL PRIORITY SUMMARY**

### **Must Have (Non-Negotiable)**
1. ✅ Next.js 14 (App Router) - **Currently Used**
2. ✅ TypeScript (Strict) - **Currently Used**
3. ✅ FastAPI + Python Async - **Currently Used**
4. ✅ SQLAlchemy 2.0 (Async) - **Currently Used**
5. ✅ RAG + LLM Integration - **Currently Used**
6. ✅ TanStack Query - **Currently Used**
7. ❌ **E2E Testing** - **MUST ADD**
8. ❌ **Mobile (React Native/Expo)** - **MUST ADD**
9. ❌ **CI/CD Pipeline** - **MUST ADD**

### **Strongly Preferred**
1. ✅ Tailwind CSS - **Currently Used**
2. ✅ Zustand - **Currently Used**
3. ✅ Pydantic v2 - **Currently Used**
4. ✅ Pinecone - **Currently Used**
5. ✅ Turborepo - **Currently Used**
6. ❌ **Error Monitoring (Sentry)** - **MUST ADD**

---

## 🎯 **CANDIDATE REQUIREMENTS**

### **Core Skills (Must Have)**
- **Next.js 14** with App Router (2+ years)
- **TypeScript** strict mode expertise
- **FastAPI** async patterns (1+ years)
- **SQLAlchemy 2.0** async ORM
- **RAG/LLM Integration** (OpenAI, Gemini)
- **Testing** (Playwright, Jest, pytest)
- **React Native/Expo** (for mobile deployment)

### **Nice to Have**
- Turborepo monorepo experience
- Supabase/PostgreSQL expertise
- Pinecone vector database
- Docker containerization

---

## ⚠️ **GAPS TO FILL**

### **Missing (Critical for Enterprise)**
1. ❌ **Testing Framework** - No tests configured
2. ❌ **Mobile App** - Not implemented
3. ❌ **CI/CD Pipeline** - No automation
4. ❌ **Error Monitoring** - No Sentry/Sentry-like
5. ❌ **Performance Monitoring** - No metrics
6. ❌ **Deployment Configuration** - Not production-ready

---

**Last Updated:** Based on current codebase analysis
**Priority:** Focus on filling gaps (Testing, Mobile, CI/CD) while maintaining current stack


