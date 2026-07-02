"""
Helpers for returning client-safe error messages.

Raw exception strings can leak API keys, database schema/SQL, file-system paths,
and other internals. Use these helpers so production responses stay generic while
developers still see full detail locally and in server logs.
"""

import logging

from config.settings import settings

logger = logging.getLogger("scholarsync.errors")


def safe_detail(exc: Exception, action: str, *, log: bool = True) -> str:
    """
    Return a client-safe error string.

    - In development: include the exception text to aid debugging.
    - In production: return only the generic ``action`` message.
    The full exception (with traceback) is always logged server-side.
    """
    if log:
        logger.error("%s: %s", action, exc, exc_info=True)
    if settings.ENVIRONMENT == "production":
        return action
    return f"{action}: {exc}"
