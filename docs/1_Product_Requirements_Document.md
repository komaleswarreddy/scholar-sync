\# Product Requirements Document (PRD)  
\#\# Project Name: ScholarSync (NotebookLM for Schools)  
\*\*Version:\*\* 2.0  
\*\*Status:\*\* Approved for Development

\#\# 1\. Executive Summary  
ScholarSync is an enterprise-grade AI "Notebook" platform for educational institutions. It replicates the source-grounded interaction model of NotebookLM but adds strict data sovereignty (Multi-Tenancy) and a centralized privacy layer. It enables students to upload school-specific study materials and interact with them via a Context-Aware Chat and a Generative Studio Suite.

\#\# 2\. Target Audience  
\* \*\*Primary Users:\*\* Students (K-12 & Higher Ed).  
\* \*\*Customers:\*\* School Administrations (B2B SaaS).

\#\# 3\. Core Value Propositions  
\* \*\*Data Sovereignty:\*\* "One School, One Interface." Data from School A is cryptographically and logically inaccessible to School B.  
\* \*\*Zero-Training Privacy:\*\* Utilization of Enterprise API tiers ensures no student data is used to train foundation models.  
\* \*\*Smart Model Routing:\*\* A backend logic layer that automatically routes tasks to the most efficient model (Gemini 1.5 Flash for heavy reading vs. GPT-4o-mini for structured generation).

\#\# 4\. Feature Scope (MVP)

\#\#\# 4.1. Source Management (Column 1\)  
**Status: ✅ Implemented (Partial)**

\* \*\*Ingestion:\*\* 
  \* ✅ **Upload PDF** - Fully implemented with background processing
  \* ⏳ **Copy/Paste Text** - UI placeholder exists, backend pending
  \* ⏳ **Add Web Links** - UI placeholder exists, backend pending
\* \*\*Selection:\*\* ✅ **Implemented** - Global "Select All" and individual toggles to include/exclude sources from the active context window
\* \*\*Deep Research:\*\* ⏳ **Planned** - "Search the web" integration UI exists but backend integration pending

\#\#\# 4.2. Chat Interface (Column 2\)  
**Status: ✅ Implemented (Core Features)**

\* \*\*RAG Pipeline:\*\* ✅ **Implemented** - Answers grounded \*strictly\* in the selected sources using Gemini 1.5 Flash
\* \*\*Citations:\*\* ✅ **Implemented** - Citations are displayed with source information and scores
  \* ⏳ **Modal View** - Clickable citations to open source paragraph in modal (UI pending)
\* \*\*History:\*\* ✅ **Implemented** - Chat history maintained per session in frontend
  \* ⏳ **Persistent Storage** - Database persistence for chat threads (backend model exists, full implementation pending)
\* \*\*Actions:\*\* 
  \* ⏳ **"Save to Note"** - Planned
  \* ⏳ **"Copy"** - Planned
  \* ⏳ **"Thumbs Up/Down"** - Planned

\#\#\# 4.3. Studio Suite (Column 3 \- Top)  
**Status: ✅ Backend Implemented, ⏳ UI Display Pending**

\* \*\*Mind Map:\*\* ✅ **Backend Ready** - Generates Markdown/Mermaid syntax for hierarchical visualization (GPT-4o-mini)
  \* ⏳ **UI Display** - Modal/view to display generated mind maps pending
\* \*\*Reports:\*\* ✅ **Backend Ready** - Generates comprehensive summaries or executive briefings (Gemini 1.5 Flash)
  \* ⏳ **UI Display** - Modal/view to display generated reports pending
\* \*\*Flashcards:\*\* ✅ **Backend Ready** - Generates JSON-structured term/definition pairs (GPT-4o-mini)
  \* ⏳ **UI Display** - Interactive flashcard view pending
\* \*\*Quiz:\*\* ✅ **Backend Ready** - Generates multiple-choice questions with answer keys and explanations (GPT-4o-mini)
  \* ⏳ **UI Display** - Interactive quiz view pending
\* \*\*Infographic:\*\* ✅ **Backend Ready** - Generates a "Visual Brief" text description for creating graphics (Gemini 1.5 Flash)
  \* ⏳ **UI Display** - Modal/view to display infographic briefs pending
\* \*\*Slide Deck:\*\* ✅ **Backend Ready** - Generates a slide-by-slide Markdown outline (GPT-4o-mini)
  \* ⏳ **UI Display** - Modal/view to display slide decks pending

\#\#\# 4.4. Notes (Column 3 \- Bottom)  
**Status: ✅ Implemented (Core Features)**

\* \*\*Pinned Content:\*\* ⏳ **Planned** - Save specific chat responses or Studio outputs
\* \*\*Manual Entry:\*\* ✅ **Implemented** - Simple text editor for creating, viewing, and deleting notes
  \* ✅ Create notes with optional source reference
  \* ✅ List all notes
  \* ✅ Delete notes

\#\#\# 4.5. Excluded Features  
\* Audio Overview (Podcasts).  
\* Video Analysis.  
\* Data Tables (CSV).

\#\# 5\. Non-Functional Requirements  
**Status: ✅ Partially Implemented**

\* \*\*Cross-Platform:\*\* 
  \* ✅ **Web (Desktop/Tablet)** - Fully implemented with Next.js 14
  \* ⏳ **Mobile (iOS/Android)** - Planned (React Native/Expo SDK 50+)
\* \*\*Latency:\*\* ✅ **Implemented** - Chat uses Server-Sent Events (SSE) for streaming, optimized for low latency
\* \*\*Security:\*\* 
  \* ✅ **Multi-Tenancy** - Implemented via subdomain-based tenant isolation
  \* ✅ **Data Isolation** - Tenant-scoped database queries and Pinecone namespaces
  \* ✅ **TLS** - HTTPS/TLS for data in transit (via deployment)
  \* ⏳ **File Encryption** - AES-256 encryption for files at rest (planned for production)  
