# TestSprite ING + RET Test Specification

Backend API base: `http://127.0.0.1:8000`

## Auth

- Header: `Authorization: Bearer <dev_jwt>` where JWT payload has `{"sub": "testsprite_user"}` (unsigned dev token accepted when CLERK not configured)
- Tenant resolved via subdomain `default` on localhost

## Fixtures

Use files in `tests/fixtures/ingestion/` (generate via `python scripts/generate_test_fixtures.py`).

## Status convention

Pass when `status == "indexed"` (this means "ready").

---

## INGESTION (ING)

### ING-01 Happy-path PDF upload
- POST `/api/v1/ingest/upload` with `standard_chapter.pdf`
- Poll GET `/api/v1/ingest/sources` until status `indexed`
- Assert chunks_count > 0
- POST `/api/v1/chat/stream` with active_source_ids and question about photosynthesis/chlorophyll
- Assert SSE includes citation events

### ING-02 TXT upload (DOCX out of scope)
- Upload `sample_phrase_alpha.txt` and `sample_phrase_beta.txt`
- Each reaches `indexed`; phrases ING02_ALPHA_PHRASE / ING02_BETA_PHRASE retrievable via chat

### ING-03 Encrypted PDF
- Upload `encrypted_sample.pdf` without password → 400 with password message
- Upload with `pdf_password=testpass` → `indexed`

### ING-04 Large file
- Upload `large_50page.pdf`; completes within 300s; status `indexed`

### ING-05 Corrupted files
- `truncated.pdf`, `jpg_renamed.pdf`, empty file → 400, never 500

### ING-06 Unsupported types
- Upload .exe, .mp4, .zip bytes → 400 before processing

### ING-07 Duplicate upload
- Same file twice → two distinct source IDs; both reach `indexed`

### ING-08 Chunking quality (sample export)
- After upload, GET sources shows chunks_count > 0 (manual rubric separate)

### ING-09 Scanned PDF
- Upload `blank_scanned.pdf` → ends `error` with image-only / no extractable text message

### ING-10 Latency
- Small TXT upload → `indexed` within 90s

### ING-11 Concurrent uploads
- 3 parallel uploads → all 200 and eventually `indexed`

---

## RETRIEVAL (RET)

### RET-01 Recall@k
- Upload `standard_chapter.pdf`, query factual questions, citations reference expected content

### RET-02 MRR
- First correct citation rank should be ≤ 3 for golden factual questions

### RET-03 Context precision
- Retrieved citation text should relate to question (no random noise)

### RET-04 Citation correctness
- Chat answer claims supported by cited chunk text

### RET-05 Multi-document
- Upload alpha + beta TXT, ask question spanning both, citations from multiple sources

### RET-06 No-answer
- Ask about Mars colonization with only photosynthesis doc → refusal / not found

### RET-07 Source isolation
- User A uploads doc; User B uses A's source_id in chat → 403

### RET-08 Paraphrase
- Same question 3 phrasings → overlapping citations in top results

### RET-09 Formula retrieval
- Upload `physics_formulas.pdf`, ask Snell's law / Henderson-Hasselbalch

### RET-10 Question types
- Definition, explanation, and question formats all return grounded answers

### RET-11 Long questions
- Multi-sentence prompt still returns relevant citations

---

## Chat API

POST `/api/v1/chat/stream`
```json
{
  "message": "...",
  "history": [],
  "active_source_ids": ["<source_uuid>"]
}
```

Expect SSE events: `citation`, `chunk`, `done`.
