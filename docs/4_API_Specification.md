\# API Specification Document  
\*\*Project:\*\* ScholarSync API  
\*\*Version:\*\* 2.0  
\*\*Base URL:\*\* \`https://api.scholarsync.com/v1\`

\#\# 1\. Authentication & Security

All API requests must be authenticated and tenant-scoped.

\#\#\# 1.1. Headers  
| Header | Required | Description |  
| :--- | :--- | :--- |  
| \`Authorization\` | Yes | Bearer Token from Clerk (JWT). Used to identify the user (\`user\_id\`). |  
| \`X-Tenant-ID\` | Yes | The subdomain string (e.g., \`greenwood\`). Used to route to the correct DB schema/namespace. |

\#\#\# 1.2. Response Codes  
\* \`200 OK\`: Success.  
\* \`401 Unauthorized\`: Missing or invalid Bearer token.  
\* \`403 Forbidden\`: User does not belong to the Tenant specified in \`X-Tenant-ID\`.  
\* \`422 Validation Error\`: Malformed JSON body (Pydantic validation failed).  
\* \`429 Too Many Requests\`: Rate limit exceeded per school/tenant.

\---

\#\# 2\. Endpoints

\#\#\# 2.1. Ingestion (Source Management)

\#\#\#\# \*\*POST\*\* \`/api/v1/ingest/upload\`  
**Status: ✅ Implemented**

Uploads a file, extracts text, chunks it, and indexes it into the Vector DB.

\* \*\*Request Content-Type:\*\* \`multipart/form-data\`  
\* \*\*Parameters:\*\*  
    \* \`file\`: (Binary) The PDF or Text file.  
    \* \`title\`: (String, Optional) Display name of the source.  
\* \*\*Process:\*\*  
    1\. ✅ Upload raw file to **Supabase Storage**: \`{tenant\_id}/{uuid}.pdf\`.  
    2\. ✅ Extract text (PyPDF).  
    3\. ✅ Split text: Configurable chunk size with overlap.  
    4\. ✅ Generate Embeddings (OpenAI \`text-embedding-3-small\`).  
    5\. ✅ Upsert to Pinecone:  
        \* \`id\`: \`{chunk\_uuid}\`  
        \* \`values\`: \`\[0.12, \-0.98, ...\]\`  
        \* \`metadata\`: \`{ "source\_id": "...", "chunk\_id": "...", "text": "...", "score": 0.0 }\`  
        \* \*\*Namespace:\*\* \`{tenant\_id}\`.  
    6\. ✅ **Background Processing:** Returns immediately with "processing" status, indexing happens asynchronously
\* \*\*Response (JSON):\*\*  
\`\`\`json  
{  
  "id": "src\_12345",  
  "title": "Physics\_Chapter\_4.pdf",  
  "status": "processing",  
  "chunks\_count": 0,  
  "created\_at": "2024-01-01T00:00:00Z"  
}
\`\`\`

#### **GET `/api/v1/ingest/sources`**

**Status: ✅ Implemented**

Retrieves a list of all sources available to the current user/tenant.

* **Response (JSON):**

\`\`\`json  
{  
  "sources": \[  
    {  
      "id": "src\_12345",  
      "title": "Physics\_Chapter\_4.pdf",  
      "type": "pdf",  
      "status": "indexed",  
      "chunks\_count": 45,  
      "created\_at": "2023-10-27T10:00:00Z",  
      "s3\_url": "https://..." \-- Presigned URL from Supabase Storage  
    }  
  \]  
}
\`\`\`

#### **DELETE `/api/v1/ingest/sources/{source_id}`**

**Status: ✅ Implemented**

Removes the source from Postgres, deletes file from Supabase Storage, and deletes all associated vectors from Pinecone.

---

### **2.2. Smart Chat (RAG Pipeline)**

**Status: ✅ Implemented**

#### **POST `/api/v1/chat/stream`**

The primary endpoint for Q\&A. Uses **Gemini 1.5 Flash** (or Gemini 2.5 Flash with fallback) for high-context handling.

* **Request Body (JSON):**

\`\`\`json  
{  
  "message": "Explain the role of mitochondria.",  
  "history": \[  
    { "role": "user", "content": "What is a cell?" },  
    { "role": "assistant", "content": "A cell is..." }  
  \],  
  "active\_source\_ids": \["src\_12345", "src\_67890"\] \-- Required, min 1 item  
}
\`\`\`

* **Process:**  
  * ✅ Embed `message` using OpenAI embeddings.  
  * ✅ Query Pinecone (Namespace: `{tenant_id}`) with filter: `source_id IN active_source_ids`.  
  * ✅ Retrieve top K chunks (configurable via `TOP_K_CHUNKS` setting).  
  * ✅ Construct System Prompt with retrieved context and citation instructions.  
  * ✅ Call Gemini API with `stream=True`.  
* **Response:** `text/event-stream` (Server-Sent Events).  
  * ✅ **Event: `citation`** \-\> JSON data `{ "source_id": "...", "chunk_id": "...", "text": "...", "score": 0.85 }`  
  * ✅ **Event: `chunk`** \-\> JSON data `{ "text": "..." }` (text tokens).  
  * ✅ **Event: `done`** \-\> End of stream `{ }`.  
  * ✅ **Event: `error`** \-\> Error information `{ "error": "..." }`.

---

### **2.3. Studio (Generative Tools)**

**Status: ✅ Backend Implemented, ⏳ UI Display Pending**

This endpoint routes tasks to the optimal model based on the `task_type`.

#### **POST `/api/v1/studio/generate`**

**Status: ✅ Implemented**

* **Request Body (JSON):**

JSON  
{  
  "task\_type": "quiz", // Options: quiz, flashcards, mind\_map, report, infographic, slide\_deck  
  "source\_ids": \["src\_12345"\],  
  "custom\_instructions": "Focus on page 10-12 only." // Optional  
}

* **Routing Logic:**  
  * **Group A (Structure/Logic):** `quiz`, `flashcards`, `mind_map`, `slide_deck`  
    * **Target Model:** **GPT-4o-mini** (OpenAI).  
    * **Reason:** Superior adherence to strict JSON/Markdown schemas.  
  * **Group B (Content/Reading):** `report`, `infographic`  
    * **Target Model:** **Gemini 1.5 Flash** (Google).  
    * **Reason:** Larger context window for comprehensive summaries.  
* **Response Models (By Task Type):**

**A. Quiz Response (JSON)**

JSON  
{  
  "task\_type": "quiz",  
  "data": {  
    "title": "Mitochondria Quiz",  
    "questions": \[  
      {  
        "question": "What is the powerhouse of the cell?",  
        "options": \["Nucleus", "Mitochondria", "Ribosome", "Golgi"\],  
        "correct\_answer": "Mitochondria",  
        "explanation": "Mitochondria generate most of the chemical energy..."  
      }  
    \]  
  }  
}

**B. Flashcards Response (JSON)**

JSON  
{  
  "task\_type": "flashcards",  
  "data": \[  
    { "front": "ATP", "back": "Adenosine Triphosphate, the energy currency." },  
    { "front": "Cristae", "back": "The folds of the inner mitochondrial membrane." }  
  \]  
}

**C. Mind Map Response (Markdown)**

JSON  
{  
  "task\_type": "mind\_map",  
  "content": "\# Cell Biology\\n\#\# Organelles\\n- Mitochondria\\n  \- Energy Production\\n  \- Double Membrane\\n- Nucleus\\n  \- DNA Storage"  
}

---

### **2.4. Notes**

**Status: ✅ Implemented**

#### **POST `/api/v1/notes`**

**Status: ✅ Implemented**

Save a note (either manual input or a saved chat response).

* **Request Body (JSON):**

\`\`\`json  
{  
  "content": "Remember to study the Krebs cycle.",  
  "source\_ref\_id": "msg\_98765" \-- Optional link to a specific chat message  
}
\`\`\`

* **Response (JSON):**

\`\`\`json  
{  
  "id": "note\_12345",  
  "content": "Remember to study the Krebs cycle."  
}
\`\`\`

#### **GET `/api/v1/notes`**

**Status: ✅ Implemented**

Returns all notes for the user.

* **Response (JSON):**

\`\`\`json  
{  
  "notes": \[  
    {  
      "id": "note\_12345",  
      "content": "Remember to study the Krebs cycle.",  
      "source\_ref\_id": "msg\_98765",  
      "created\_at": "2024-01-01T00:00:00Z"  
    }  
  \]  
}
\`\`\`

#### **DELETE `/api/v1/notes/{note_id}`**

**Status: ✅ Implemented**

Deletes a note by ID.

---

## **3\. Data Schemas (Pydantic Models)**

### **ChatRequest**

Python  
class ChatRequest(BaseModel):  
    message: str  
    history: List\[Dict\[str, str\]\] \= \[\] \# \[{"role": "user", "content": "..."}\]  
    active\_source\_ids: List\[str\]

### **StudioRequest**

Python  
class StudioRequest(BaseModel):  
    task\_type: Literal\['quiz', 'flashcards', 'mind\_map', 'report', 'infographic', 'slide\_deck'\]  
    source\_ids: List\[str\]  
    custom\_instructions: Optional\[str\] \= None

### **SourceMetadata**

Python  
class SourceMetadata(BaseModel):  
    source\_id: str  
    page\_number: int  
    chunk\_text: str  
    score: float \# Vector similarity score  
