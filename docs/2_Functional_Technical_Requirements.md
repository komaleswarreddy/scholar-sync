\# Functional & Technical Requirements Document (FRD/TRD)

\#\# 1\. Multi-Tenancy & Security Logic

\#\#\# 1.1. Tenant Identification  
\* \*\*Mechanism:\*\* Subdomain Extraction.  
    \* URL: \`https://lincoln.scholarsync.com\` \-\> \`tenant\_id \= lincoln\`.  
\* \*\*Middleware:\*\* Next.js Middleware must intercept the request, look up the \`school\_id\` from the \`tenants\` table, and inject it into the API headers.

\#\#\# 1.2. Data Isolation (The "Iron Wall")  
**Status: ✅ Implemented**

\* \*\*Database (Postgres):\*\* ✅ Tenant-scoped queries via middleware
    \* \*Implementation:\* All database queries filter by \`tenant\_id\` extracted from subdomain
    \* \*Middleware:\* \`tenant\_middleware\` extracts subdomain and injects \`tenant\_id\` into request state
    \* ⏳ \*Future:\* Row Level Security (RLS) policies for additional security layer
\* \*\*Vector Database (Pinecone):\*\* ✅ Strict Namespace segregation implemented
    \* \*Format:\* \`namespace="{tenant\_id}"\` (using UUID from database)
    \* \*Query Rule:\* ✅ Every vector search includes tenant namespace
    \* \*Storage:\* ✅ Files stored in tenant-scoped paths: \`{tenant\_id}/{file\_id}.pdf\`

\#\#\# 1.3. The "Smart Router" (AI Dispatcher)  
**Status: ✅ Implemented**

The backend programmatically decides which model to call:  
\* \*\*Context-Heavy Tasks (Chat, Reports, Infographics):\*\* ✅ Route to \*\*Gemini 1.5 Flash\*\* (or Gemini 2.5 Flash with fallback)
    \* ✅ Handles large context windows efficiently
    \* ✅ Used for: Chat responses, comprehensive reports, infographic briefs
\* \*\*Structured Tasks (Quiz, JSON, Flashcards, Mind Maps, Slide Decks):\*\* ✅ Route to \*\*GPT-4o-mini\*\*
    \* ✅ Adheres to strict JSON schemas or Markdown formatting instructions
    \* ✅ Used for: Quiz generation, flashcards (JSON), mind maps (Markdown), slide decks (Markdown)

\#\# 2\. Technical Constraints & Architecture

\#\#\# 2.1. Shared Codebase (Monorepo)  
\* \*\*Structure:\*\* TurboRepo or Nx.  
\* \*\*Shared Logic:\*\* API Clients, Zod Schemas, Types, and Zustand Stores must be in a shared \`packages/\` directory to be consumed by both the Next.js Web App and React Native Mobile App.

\#\#\# 2.2. Frontend  
\* \*\*Web:\*\* Next.js 14 (App Router) for Server Side Rendering (SSR) and SEO.  
\* \*\*Mobile:\*\* React Native (Expo SDK 50+) for Over-the-Air updates and native access.  
\* \*\*Styling:\*\* Tailwind CSS (Web) and NativeWind (Mobile) to share design tokens.

\#\#\# 2.3. Backend  
\* \*\*Framework:\*\* FastAPI (Python).  
\* \*\*Concurrency:\*\* Must use \`async/await\` for all DB and LLM calls to handle high concurrency.  
\* \*\*Streaming:\*\* All Chat/Studio generation endpoints must return \`StreamingResponse\` (Server-Sent Events) to minimize perceived latency.

\#\#\# 2.4. Data Storage  
\* \*\*Blob Storage:\*\* AWS S3 (Private Buckets).  
\* \*\*Vectors:\*\* Pinecone (Serverless Index).  
