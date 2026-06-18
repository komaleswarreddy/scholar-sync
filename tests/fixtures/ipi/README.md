# IPI poisoned fixtures (TEST-ONLY)

These PDFs contain **indirect prompt injection payloads** for automated safety testing.

## Access control

- **Do not** upload to production tenants, shared knowledge bases, or student-facing environments.
- **Do not** commit real student data alongside these files.
- Restrict repository access to engineers running the IPI bucket.

## Regenerate

```powershell
python scripts/generate_ipi_fixtures.py
python scripts/log_ipi_ingestion_survival.py
```

## Manifest

See [`manifest.json`](manifest.json) for version, hiding method, and payload hashes per file.
