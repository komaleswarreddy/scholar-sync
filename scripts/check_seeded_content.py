"""Quick audit: NCERT global library rows in DB and Pinecone namespace stats."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, text
from config.settings import settings


def _sync_db_url() -> str:
    url = settings.DATABASE_URL
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def check_db() -> None:
    print("=== Database (NCERT Global Library) ===")
    engine = create_engine(_sync_db_url())
    with engine.connect() as conn:
        queries = [
            ("SELECT COUNT(*) FROM ncert_global_documents", "ncert_global_documents total"),
            (
                "SELECT COUNT(*) FROM ncert_global_documents "
                "WHERE status IN ('indexed', 'completed')",
                "indexed/completed documents",
            ),
            ("SELECT COUNT(*) FROM ncert_global_ingestion_runs", "ingestion_runs"),
            ("SELECT COUNT(*) FROM sources", "user sources"),
            ("SELECT COUNT(*) FROM notebooks", "notebooks"),
        ]
        for sql, label in queries:
            try:
                count = conn.execute(text(sql)).scalar()
                print(f"  {label}: {count}")
            except Exception as exc:
                print(f"  {label}: ERROR - {exc}")

        try:
            rows = conn.execute(
                text(
                    "SELECT class, subject, chapter_no, chapter_name, status "
                    "FROM ncert_global_documents "
                    "ORDER BY class, subject, chapter_no LIMIT 25"
                )
            ).fetchall()
            print("  sample documents:")
            if not rows:
                print("    (none)")
            else:
                for row in rows:
                    print(f"    class={row[0]} subject={row[1]} ch={row[2]} name={row[3]!r} status={row[4]}")
        except Exception as exc:
            print(f"  sample documents: ERROR - {exc}")


def check_pinecone() -> None:
    print("\n=== Pinecone ===")
    print(f"  index: {settings.PINECONE_INDEX_NAME}")
    print(f"  NCERT namespace: {settings.NCERT_GLOBAL_PINECONE_NAMESPACE}")
    if not settings.PINECONE_API_KEY:
        print("  PINECONE_API_KEY not set — skipping stats")
        return
    try:
        from pinecone import Pinecone

        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX_NAME)
        stats = index.describe_index_stats()
        namespaces = stats.get("namespaces") or {}
        ncert_ns = namespaces.get(settings.NCERT_GLOBAL_PINECONE_NAMESPACE)
        total_vectors = stats.get("total_vector_count", 0)
        print(f"  total vectors (all namespaces): {total_vectors}")
        if ncert_ns:
            print(f"  NcertDataGlobal vector_count: {ncert_ns.get('vector_count', 0)}")
        else:
            print("  NcertDataGlobal namespace: not present or empty")
        print(f"  namespace keys: {list(namespaces.keys())[:10]}")
    except Exception as exc:
        print(f"  Pinecone check ERROR - {exc}")


if __name__ == "__main__":
    check_db()
    check_pinecone()
