# NotebookLM (ScholarSync) — Product Requirements for TestSprite

## Product overview

NotebookLM is an AI notebook platform for educational institutions. Users upload documents (PDF, TXT), the system ingests/chunks/embeds them into Pinecone, and users chat with grounded answers citing source chunks via SSE streaming.

**Local API:** `http://localhost:8000`

## Core user flows

### 1. Document ingestion

- **Upload:** `POST /api/v1/ingest/upload` (multipart: `file`, optional `title`, `pdf_password`)
- **List sources:** `GET /api/v1/ingest/sources`
- **Delete source:** `DELETE /api/v1/ingest/sources/{source_id}`
- **Status lifecycle:** `processing` → `indexed` (success) or `error` (failure)
- **Supported types:** PDF, TXT only (max 10MB)
- **Tenant isolation:** Pinecone namespace per tenant; user isolation via `source_id` ownership

### 2. RAG chat

- **Stream chat:** `POST /api/v1/chat/stream` (JSON body: `message`, `history`, `active_source_ids`)
- **Response:** Server-Sent Events with `citation`, `chunk`, `done` events
- **Grounding:** Answers must cite uploaded sources; out-of-corpus questions should refuse with "not found" messaging
- **Security:** `active_source_ids` must belong to authenticated user; cross-user access returns 403

### 3. Authentication (development)

- Header: `Authorization: Bearer <jwt>`
- Dev JWT (unsigned): payload `{"sub": "test_user_id"}` — accepted when Clerk not fully configured
- Tenant resolved from subdomain `default` on localhost

## Test fixtures

Located at `tests/fixtures/ingestion/` (run `python scripts/generate_test_fixtures.py`):

| File | Purpose |
|------|---------|
| standard_chapter.pdf | Happy-path PDF with photosynthesis content |
| sample_phrase_alpha.txt | Contains ING02_ALPHA_PHRASE |
| sample_phrase_beta.txt | Contains ING02_BETA_PHRASE |
| encrypted_sample.pdf | Password: `testpass` |
| large_50page.pdf | Performance / large doc |
| truncated.pdf | Corrupt PDF |
| jpg_renamed.pdf | Fake PDF |
| blank_scanned.pdf | Image-only PDF (no text) |
| physics_formulas.pdf | Snell's law, Henderson-Hasselbalch |

## Required test cases (ING + RET)

### Ingestion gates

| ID | Test | Pass criteria |
|----|------|---------------|
| ING-01 | PDF upload | status=`indexed`, chunks>0, chat retrieves content |
| ING-02 | TXT upload | Both TXT fixtures indexed and retrievable |
| ING-03 | Encrypted PDF | No password→400; with password→indexed |
| ING-04 | Large PDF | indexed within 300s |
| ING-05 | Corrupt files | 400 errors, never 500 |
| ING-06 | Unsupported types | .exe/.mp4/.zip rejected with 400 |
| ING-07 | Duplicate upload | Two unique source IDs, both indexed |
| ING-08 | Chunk quality | chunks_count>0 after upload |
| ING-09 | Scanned PDF | error status with clear image-only message |
| ING-10 | Latency | Small upload indexed within 90s |
| ING-11 | Concurrent | 3 parallel uploads all succeed |

### Retrieval gates

| ID | Test | Pass criteria |
|----|------|---------------|
| RET-01 | Recall | Factual questions return relevant citations |
| RET-02 | MRR | Correct chunk in top 3 |
| RET-03 | Precision | Citations relate to question |
| RET-04 | Citation correctness | Answer supported by cited text |
| RET-05 | Multi-doc | Citations from multiple sources |
| RET-06 | No-answer | Out-of-corpus refusal, no hallucination |
| RET-07 | Isolation | User B cannot use User A source (403) |
| RET-08 | Paraphrase | Similar citations across phrasings |
| RET-09 | Formulas | Snell's law / Henderson-Hasselbalch retrieved |
| RET-10 | Question types | Definition, explanation, Q&A all work |
| RET-11 | Long questions | Multi-sentence prompts still grounded |

## API examples

### Upload

```
POST /api/v1/ingest/upload
Authorization: Bearer <jwt>
Content-Type: multipart/form-data
file: standard_chapter.pdf
```

### Chat

```
POST /api/v1/chat/stream
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "message": "What role does chlorophyll play?",
  "history": [],
  "active_source_ids": ["<source-uuid>"]
}
```

## Non-functional requirements

- No 500 errors on invalid uploads (use 400)
- Indexed status means document is ready for chat
- Health check: `GET /health` returns 200
