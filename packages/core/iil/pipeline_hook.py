"""Non-blocking hook to schedule InteractionLog creation after chat responses."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from config.settings import settings
from packages.core.database.connection import AsyncSessionLocal
from packages.core.iil.interaction_log_service import create_interaction_log, trace_from_debug
from packages.core.iil.trace_payload import PipelineTracePayload

logger = logging.getLogger(__name__)


async def _run_log_task(
    message_id: str,
    tenant_id: str,
    user_id: str,
    trace: PipelineTracePayload,
) -> None:
    if not settings.IIL_ENABLED:
        return
    timeout = max(5.0, settings.IIL_LOGGING_ASYNC_TIMEOUT_MS / 1000.0)
    try:
        async with AsyncSessionLocal() as db:
            log = await asyncio.wait_for(
                create_interaction_log(
                    db,
                    message_id=message_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    trace=trace,
                ),
                timeout=timeout,
            )
            if log:
                logger.info("IIL: log task ok message_id=%s log_id=%s", message_id, log.id)
            else:
                logger.warning("IIL: log task returned None for message_id=%s", message_id)
    except asyncio.TimeoutError:
        logger.error("IIL: InteractionLog creation timed out for message %s", message_id)
    except Exception as exc:
        logger.error("IIL: InteractionLog creation failed for message %s: %s", message_id, exc)


def schedule_interaction_log(
    message_id: str,
    tenant_id: str,
    user_id: str,
    trace: Optional[PipelineTracePayload] = None,
    debug_trace: Optional[Dict[str, Any]] = None,
    **trace_kwargs: Any,
) -> None:
    """Fire-and-forget InteractionLog creation (never blocks chat path)."""
    if not settings.IIL_ENABLED:
        return
    payload = trace or trace_from_debug(debug_trace, **trace_kwargs)
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run_log_task(message_id, tenant_id, user_id, payload))
    except RuntimeError:
        asyncio.run(_run_log_task(message_id, tenant_id, user_id, payload))
