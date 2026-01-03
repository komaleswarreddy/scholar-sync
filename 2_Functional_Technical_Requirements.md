\# Functional & Technical Requirements Document (FRD/TRD)

\#\# 1\. Multi-Tenancy & Security Logic

\#\#\# 1.1. Tenant Identification  
\* \*\*Mechanism:\*\* Subdomain Extraction.  
    \* URL: \`https://lincoln.scholarsync.com\` \-\> \`tenant\_id \= lincoln\`.  
\* \*\*Middleware:\*\* Next.js Middleware must intercept the request, look up the \`school\_id\` from the \`tenants\` table, and inject it into the API headers.

\#\#\# 1.2. Data Isolation (The "Iron Wall")  
\* \*\*Database (Postgres):\*\* Row Level Security (RLS) policies must be enabled.  
    \* \*Policy:\* \`CREATE POLICY tenant\_isolation ON sources USING (school\_id \= current\_setting('app.current\_school\_id'));\`  
\* \*\*Vector Database (Pinecone):\*\* strict Namespace segregation.  
    \* \*Format:\* \`namespace="{school\_id}"\`.  
    \* \*Query Rule:\* Every vector search \*must\* include this namespace.

\#\#\# 1.3. The "Smart Router" (AI Dispatcher)  
The backend must programmatically decide which model to call:  
\* \*\*Context-Heavy Tasks (Chat, Reports):\*\* Route to \*\*Gemini 1.5 Flash\*\*.  
    \* \*Requirement:\* Must handle context windows \> 100k tokens cheaply.  
\* \*\*Structured Tasks (Quiz, JSON, Flashcards, Mind Maps):\*\* Route to \*\*GPT-4o-mini\*\*.  
    \* \*Requirement:\* Must adhere to strict JSON schemas or Markdown formatting instructions (System Prompts).

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
