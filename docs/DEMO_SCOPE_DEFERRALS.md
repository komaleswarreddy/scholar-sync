# Demo Scope Deferrals (KNOWN_GAP)

Explicit product decisions for capabilities **not** included in the current demo launch. These are intentional deferrals, not test failures.

| Test ID | Deferred capability | Demo behavior | User-facing message |
|---------|---------------------|---------------|---------------------|
| **ING-02** | Microsoft Word (`.docx`) ingestion | PDF and TXT upload/index/search work normally | `File type '.docx' is not supported. Only PDF and text files are allowed.` (HTTP 400) |
| **ING-04** | Full 100+ page NCERT textbook corpus | 50-page synthetic PDF indexes within 300s SLA in automated tests | Oversize or timeout returns clear ingest error with guidance to split or use PDF under size limit |

## Rationale

- **ING-02:** DOCX parsing and layout preservation require a dedicated pipeline (not yet scoped for demo). Real teachers often upload Word files; this gap is documented so support knows to ask for PDF export.
- **ING-04:** End-to-end validation against full NCERT volumes is a data and SLA project separate from core RAG correctness. Demo proves indexing SLA on representative large PDFs, not every official textbook length.

## Product owner sign-off

| Field | Value |
|-------|-------|
| Accepted for demo launch | Yes — deferrals documented |
| Product owner | _________________________________ |
| Date | _________________________________ |

## Related docs

- [ING_RET_TEST_SUITE.md](ING_RET_TEST_SUITE.md) — full test matrix
- [PROD_GATE_SCORECARD.md](PROD_GATE_SCORECARD.md) — gate status (KNOWN_GAP rows)
- [PRODUCTION_TEST_REPORT.md](PRODUCTION_TEST_REPORT.md) — engineering evidence
