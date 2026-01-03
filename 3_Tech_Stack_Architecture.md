\# Tech Stack & Architecture Document  
\*\*Project:\*\* ScholarSync  
\*\*Type:\*\* Monorepo (Web \+ Mobile)

\#\# 1\. Technology Stack (Detailed)

\#\#\# 1.1. Monorepo & Build System  
\* \*\*Manager:\*\* \`Turborepo\` (for high-performance build caching).  
\* \*\*Package Manager:\*\* \`pnpm\` (Workspace support).  
\* \*\*Language:\*\* \`TypeScript 5.3+\` (Strict mode enabled).

\#\#\# 1.2. Frontend \- Web (Dashboard)  
\* \*\*Framework:\*\* \`Next.js 14\` (App Router).  
\* \*\*Rendering:\*\* Server Components (RSC) by default; Client Components for Chat/Studio.  
\* \*\*State Management:\*\* \`Zustand\` (Global store for sources/user prefs).  
\* \*\*Data Fetching:\*\* \`TanStack Query (React Query) v5\` (for caching API responses).  
\* \*\*Form Handling:\*\* \`React Hook Form\` \+ \`Zod\` (Validation).  
\* \*\*UI Components:\*\* \`Radix UI\` (Headless accessibility) \+ \`Tailwind CSS\`.  
\* \*\*Markdown Rendering:\*\* \`react-markdown\` \+ \`remark-gfm\` \+ \`rehype-highlight\`.  
\* \*\*PDF Viewer:\*\* \`@react-pdf-viewer/core\` (Web-specific).

\#\#\# 1.3. Frontend \- Mobile (iOS/Android)  
\* \*\*Framework:\*\* \`React Native\` via \`Expo SDK 50\`.  
\* \*\*Router:\*\* \`expo-router\` (File-based routing, matches Next.js structure).  
\* \*\*Styling:\*\* \`NativeWind v4\` (Uses Tailwind classes on Native components).  
\* \*\*Components:\*\* \`Tamagui\` or \`React Native Paper\` (adapted to dark mode).  
\* \*\*PDF Viewer:\*\* \`react-native-pdf\`.  
\* \*\*Storage:\*\* \`react-native-mmkv\` (Fastest key-value storage for local user prefs).

\#\#\# 1.4. Backend (API Gateway & Processing)  
\* \*\*Framework:\*\* \`FastAPI\` (Python 3.11).  
\* \*\*Server:\*\* \`Uvicorn\` (ASGI).  
\* \*\*Database ORM:\*\* \`Prisma Client Python\` or \`SQLAlchemy 2.0\` (Async).  
\* \*\*Vector Ops:\*\* \`Pinecone Python Client\`.  
\* \*\*LLM Orchestration:\*\*  
    \* \`google-generativeai\` (Gemini).  
    \* \`openai\` (GPT-4o).  
    \* \`langchain-text-splitters\` (Recursive character splitting).  
\* \*\*File Handling:\*\* \`python-multipart\` (Uploads), \`pypdf\` (Parsing).

\#\#\# 1.5. Infrastructure & Database  
\* \*\*Primary DB:\*\* \`Supabase\` (PostgreSQL 15).  
    \* \*Extensions:\* \`pg\_trgm\` (Search), \`uuid-ossp\`.  
\* \*\*Vector DB:\*\* \`Pinecone\` (Serverless).  
\* \*\*Auth:\*\* \`Clerk\` (Handles JWTs, Sessions, Multi-Tenancy).  
\* \*\*Storage:\*\* \`AWS S3\` (Standard Class) or \`Supabase Storage\`.  
\* \*\*Logging:\*\* \`Axiom\` or \`Sentry\`.

\---

\#\# 2\. Architecture & Data Flow

\#\#\# 2.1. System Context Diagram (Mermaid)  
\`\`\`mermaid  
graph TD  
    UserWeb\[Web Client (Next.js)\] \--\>|HTTPS/JSON| Middleware\[Next.js Middleware\]  
    UserMobile\[Mobile Client (Expo)\] \--\>|HTTPS/JSON| Middleware  
      
    Middleware \--\>|Auth Check| Clerk\[Clerk Auth\]  
    Middleware \--\>|Pass Request \+ TenantID| Backend\[FastAPI Gateway\]  
      
    Backend \--\>|Read/Write| Postgres\[Supabase DB\]  
    Backend \--\>|Vector Search| Pinecone\[Pinecone Vector DB\]  
      
    Backend \--\>|Stream Chat| Gemini\[Google Gemini API\]  
    Backend \--\>|Generate JSON| OpenAI\[OpenAI API\]

### **2.2. Critical Data Flows**

**A. Ingestion Pipeline (Upload):**

1. **Client:** Uploads PDF \-\> Sends `FormData` to `/api/ingest`.  
2. **FastAPI:**  
   * Validates file type/size.  
   * Uploads raw file to S3 (Key: `{tenant_id}/{uuid}.pdf`).  
   * Extracts text using `pypdf`.  
   * Cleans text (removes headers/footers).  
   * Splits into 1000-character chunks (overlap 200).  
   * Generates Embeddings (via OpenAI `text-embedding-3-small` or Gemini).  
   * Upserts to Pinecone: `id={chunk_id}`, `values=[...]`, `metadata={source_id, page_num, text}`.  
   * **Namespace:** `{tenant_id}`.

**B. Chat Pipeline (RAG):**

1. **Client:** Sends message \+ list of `active_source_ids`.  
2. **FastAPI:**  
   * Embeds user query.  
   * Queries Pinecone: `filter={ source_id: { $in: active_source_ids } }`.  
   * Retrieves top 10 chunks.  
   * Constructs Prompt: "Context: \[Chunks\]... Question: \[Query\]".  
   * Calls Gemini 1.5 Flash (Stream=True).  
3. **Response:** Streams chunks to client via SSE (Server-Sent Events).

---

## **3\. Directory Structure (Monorepo)**

/  
├── apps/  
│   ├── web/                  \# Next.js Application  
│   │   ├── app/              \# App Router  
│   │   │   ├── (auth)/       \# Login/Register routes  
│   │   │   ├── \[subdomain\]/  \# Tenant Dynamic Route  
│   │   │   │   ├── dashboard/  
│   │   │   │   │   ├── page.tsx  
│   │   │   │   │   ├── layout.tsx (3-Column Grid)  
│   │   ├── components/       \# Web-specific components  
│   │   ├── lib/              \# Web-specific utils  
│   │   └── tailwind.config.ts  
│   │  
│   └── mobile/               \# Expo Application  
│       ├── app/              \# Expo Router  
│       │   ├── (tabs)/       \# Tab Navigation  
│       │   ├── chat/\[id\].tsx \# Chat Screen  
│       ├── components/       \# Native-specific components  
│       └── babel.config.js  
│  
├── packages/                 \# Shared Code  
│   ├── ui/                   \# Shared UI Components (if using universal lib)  
│   ├── api/                  \# API Client (Axios/Fetch wrappers)  
│   ├── types/                \# Shared TypeScript Interfaces (Zod schemas)  
│   ├── config/               \# Shared ESLint/TSConfig  
│   └── icons/                \# Shared Lucide Icons  
│  
├── backend/                  \# Python FastAPI  
│   ├── app/  
│   │   ├── api/  
│   │   │   ├── v1/  
│   │   │   │   ├── endpoints/  
│   │   │   │   │   ├── chat.py  
│   │   │   │   │   ├── sources.py  
│   │   │   │   │   └── studio.py  
│   │   ├── core/             \# Config, Security, Events  
│   │   ├── services/         \# Business Logic (RAG, LLM calls)  
│   │   └── models/           \# Pydantic Models  
│   ├── requirements.txt  
│   └── Dockerfile  
│  
├── turbo.json                \# Turborepo config  
└── package.json              \# Root scripts

4\. Database Schema (PostgreSQL)

\-- Managed by Supabase / Prisma

CREATE TABLE tenants (  
  id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),  
  subdomain TEXT UNIQUE NOT NULL, \-- "greenwood"  
  name TEXT NOT NULL,  
  settings JSONB \-- { "primary\_color": "\#ff0000" }  
);

CREATE TABLE sources (  
  id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),  
  tenant\_id UUID REFERENCES tenants(id),  
  title TEXT NOT NULL,  
  s3\_key TEXT NOT NULL,  
  type TEXT DEFAULT 'pdf', \-- 'pdf', 'url', 'text'  
  created\_at TIMESTAMPTZ DEFAULT NOW()  
);

CREATE TABLE chats (  
  id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),  
  tenant\_id UUID REFERENCES tenants(id),  
  user\_id TEXT NOT NULL, \-- Clerk User ID  
  title TEXT,  
  created\_at TIMESTAMPTZ DEFAULT NOW()  
);

CREATE TABLE messages (  
  id UUID PRIMARY KEY DEFAULT gen\_random\_uuid(),  
  chat\_id UUID REFERENCES chats(id),  
  role TEXT NOT NULL, \-- 'user', 'assistant'  
  content TEXT NOT NULL,  
  citations JSONB \-- Array of reference indices  
);  
