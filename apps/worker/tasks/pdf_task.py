"""
Source Ingestion Task

Celery task that runs source ingestion (text extraction, chunking,
embedding, Pinecone upsert, status update) fully out-of-process from
the API server — an opt-in alternative to FastAPI BackgroundTasks.
See apps/api/routes/sources.py (ENABLE_CELERY_INGESTION flag) and
apps/worker/celery_app.py (how to run a worker).

IMPORTANT — why this task only takes primitive string arguments:
Celery sends task arguments over the broker as JSON (task_serializer
="json" in celery_app.py). A FastAPI-injected AsyncSession, SQLAlchemy
ORM objects, or raw file bytes are either not JSON-serializable or
unsafe/wasteful to ship through a message queue. This task therefore
accepts only identifiers (source_id, tenant_id, user_id, content_type,
optional pdf_password) and re-fetches everything it needs — the S3
object, the Source row — itself, via its OWN fresh DB session created
inside the task (Celery workers are separate sync processes; they
cannot share the API process's request-scoped AsyncSession).
"""

import asyncio

from apps.worker.celery_app import celery_app


@celery_app.task(
    name="apps.worker.tasks.pdf_task.process_source_ingestion",
    bind=True,
    # Conservative default: no automatic retries. The ingestion pipeline
    # (packages/core/services/source_service.py IngestionService.process_file_background)
    # is not idempotent — re-running it after a partial failure would re-chunk,
    # re-embed, and re-upsert into Pinecone, duplicating vectors before any prior
    # partial write is cleaned up. On failure it already marks the Source row
    # status="error" with a message, which is the correct signal for the user/UI
    # to see and retry from (e.g. via a future re-ingest action), rather than a
    # silent, automatic Celery-level retry.
    max_retries=0,
)
def process_source_ingestion(
    self,
    tenant_id: str,
    user_id: str,
    source_id: str,
    content_type: str,
    pdf_password: str | None = None,
) -> dict:
    """
    Celery task entrypoint (runs in a sync worker process).

    Celery tasks are plain sync functions; the actual ingestion logic is
    async (async DB session, async S3/embedding/Pinecone calls). asyncio.run(...)
    creates a brand-new event loop for the lifetime of this single task
    invocation and tears it down when done — the standard pattern for calling
    async code from sync Celery tasks. Do not reuse a loop across tasks: each
    invocation may run in a different worker thread/process depending on the
    pool (--pool=solo / --pool=threads / --pool=prefork).
    """
    try:
        asyncio.run(
            _run_ingestion(
                tenant_id=tenant_id,
                user_id=user_id,
                source_id=source_id,
                content_type=content_type,
                pdf_password=pdf_password,
            )
        )
        return {"source_id": source_id, "status": "ok"}
    except Exception as exc:
        # process_upload_background (invoked below) already catches its own
        # exceptions, logs them, and writes status="error" + error_message onto
        # the Source row — it does not re-raise. This except block is a last-resort
        # safety net for anything that fails *before* that (e.g. an import error,
        # or the DB session itself failing to open). We deliberately do not
        # re-raise here: with max_retries=0, letting this propagate would only
        # mark the Celery task FAILED in the result backend without providing any
        # additional recovery — the Source row is the real source of truth for
        # ingestion status, not the Celery task result.
        print(f"[CELERY] Ingestion task failed for source {source_id}: {exc}")
        return {"source_id": source_id, "status": "error", "error": str(exc)}


async def _run_ingestion(
    tenant_id: str,
    user_id: str,
    source_id: str,
    content_type: str,
    pdf_password: str | None,
) -> None:
    """
    Async body of the task, run inside the fresh event loop created by
    asyncio.run() above.

    Import is deferred (rather than at module top-level) so that importing
    this task module — which happens at Celery worker startup via
    celery_app.py's `include=[...]` — does not pull in the full FastAPI
    route/schema import graph unless a task actually executes.

    Reuses process_upload_background as-is (rather than duplicating its
    extract/chunk/embed/upsert/error-handling logic here) so the Celery path
    and the existing BackgroundTasks path behave identically — including
    updating the Source row to status="error" with a message on failure.
    It already opens its own fresh AsyncSessionLocal() session internally,
    which is exactly what a Celery task (a separate process from the API)
    needs: it cannot use a request-scoped AsyncSession from the API process.
    """
    from apps.api.routes.sources import process_upload_background

    await process_upload_background(tenant_id, user_id, source_id, content_type, pdf_password)
