"""
Celery Application

Real Celery() app instance used for out-of-process ingestion (see
apps/worker/tasks/pdf_task.py). Broker and result backend default to
REDIS_URL (the same Redis already used elsewhere in this codebase for
caching) — override with CELERY_BROKER_URL / CELERY_RESULT_BACKEND in
config/settings.py if you want a dedicated Redis instance/db index.

=====================================================================
HOW TO RUN A WORKER LOCALLY (this is a Windows dev machine)
=====================================================================
1. Make sure Redis is reachable at REDIS_URL (config/settings.py).
   Easiest: `docker compose up redis` (see docker-compose.yml at the
   repo root), or point REDIS_URL at any Redis you already have.

2. Install worker dependencies. `celery` is NOT part of the API's
   minimal runtime import graph — install it explicitly:
       pip install "celery[redis]>=5.3.0" "redis>=5.0.0"
   (also listed in requirements.txt / pyproject.toml's `worker` extra)

3. Start a worker from the repo root. Celery's default "prefork" pool
   uses os.fork(), which does not exist on Windows — you MUST select a
   Windows-safe pool implementation:

       celery -A apps.worker.celery_app worker --loglevel=info --pool=solo

   or, for a bit of concurrency (ingestion is I/O-bound — network calls
   to S3/OpenAI/Pinecone — so threads help even though solo is single
   threaded):

       celery -A apps.worker.celery_app worker --loglevel=info --pool=threads --concurrency=4

4. Confirm the worker log shows the task registered before relying on it:
       [tasks]
         . apps.worker.tasks.pdf_task.process_source_ingestion

5. ONLY once you see the worker connected to Redis and the task listed
   above, flip the feature flag (requires an API restart to take effect):
       ENABLE_CELERY_INGESTION=true   (in .env)

=====================================================================
DANGER: do not flip the flag without a worker running
=====================================================================
ENABLE_CELERY_INGESTION defaults to False in config/settings.py. If it
is set True but no worker is running/connected to the same Redis
broker, uploads still appear to succeed (the Source row is created),
but ingestion NEVER runs: the task message sits in the Redis queue
indefinitely, the Source stays stuck at status="processing" forever,
and nothing is ever indexed into Pinecone. There is no error and no
timeout surfaced to the user — it silently looks fine until someone
tries to chat with that source and gets no context. Always verify a
worker is running (step 4 above) before enabling this flag anywhere.
=====================================================================
"""

from celery import Celery

from config.settings import settings

_broker_url = settings.CELERY_BROKER_URL or settings.REDIS_URL
_result_backend = settings.CELERY_RESULT_BACKEND or settings.REDIS_URL

celery_app = Celery(
    "scholarsync",
    broker=_broker_url,
    backend=_result_backend,
    # Import path(s) so `celery -A apps.worker.celery_app worker` registers tasks
    # without requiring a separate autodiscover step.
    include=["apps.worker.tasks.pdf_task"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    # Ingestion (contextual retrieval enrichment, embeddings, Pinecone upsert) can take
    # minutes for large documents. Hard-kill at this ceiling so a stuck task doesn't
    # occupy a worker slot forever; the soft limit gives the task a chance to notice
    # first (raises SoftTimeLimitExceeded inside the task rather than killing it cold).
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT_SECONDS,
    task_soft_time_limit=max(settings.CELERY_TASK_TIME_LIMIT_SECONDS - 30, 30),
    # Reasonable default worker concurrency. Irrelevant when running with
    # --pool=solo on Windows (always effectively 1); used if a worker is later run
    # with --pool=threads/--pool=prefork (e.g. in the Linux Docker deployment).
    worker_concurrency=4,
    # Ingestion is not idempotent (re-running duplicates Pinecone upserts before old
    # vectors are cleaned up), so avoid aggressive redelivery/prefetch behavior.
    task_acks_late=False,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    enable_utc=True,
)
