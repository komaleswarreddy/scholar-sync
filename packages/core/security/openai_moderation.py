from __future__ import annotations

from typing import Any, Dict

from config.settings import settings


def _get_openai_client():
    try:
        import openai
        try:
            import httpx
        except Exception:
            httpx = None
    except Exception as e:  # pragma: no cover
        raise ValueError("OpenAI package not installed") from e

    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your-openai-api-key":
        raise ValueError("OpenAI API key not configured. Please set OPENAI_API_KEY in .env")

    # Use an explicit httpx client to avoid proxy-related issues and ensure timeouts.
    if httpx is not None:
        http_client = httpx.Client(timeout=60.0)
        return openai.OpenAI(api_key=settings.OPENAI_API_KEY, http_client=http_client)
    return openai.OpenAI(api_key=settings.OPENAI_API_KEY)


def check_moderation(text: str, model: str | None = None) -> Dict[str, Any]:
    """
    Call OpenAI Moderation API and return a normalized result.

    Returns:
      {
        "flagged": bool,
        "categories": dict,
        "category_scores": dict
      }
    """
    if model is None:
        model = getattr(settings, "OPENAI_MODERATION_MODEL", "omni-moderation-latest")

    if not text or not text.strip():
        return {"flagged": False, "categories": {}, "category_scores": {}}

    client = _get_openai_client()
    resp = client.moderations.create(model=model, input=text)

    # OpenAI returns a list of results
    results = getattr(resp, "results", None) or []
    first = results[0] if results else None
    if first is None:
        return {"flagged": False, "categories": {}, "category_scores": {}}

    flagged = bool(getattr(first, "flagged", False))
    categories = getattr(first, "categories", None) or {}
    category_scores = getattr(first, "category_scores", None) or {}

    # Convert possible pydantic objects to dicts
    if hasattr(categories, "model_dump"):
        categories = categories.model_dump()
    if hasattr(category_scores, "model_dump"):
        category_scores = category_scores.model_dump()

    return {
        "flagged": flagged,
        "categories": categories,
        "category_scores": category_scores,
    }


def should_block_from_category_scores(
    result: dict[str, Any],
    threshold: float | None = None,
) -> bool:
    """
    Supplement OpenAI's top-level `flagged` bit: block if any category score is high enough.
    Prevents borderline adult/harassment prompts from reaching RAG and returning
    \"Not found in provided sources.\"
    """
    from config.settings import settings

    if threshold is None:
        threshold = float(
            getattr(settings, "MODERATION_CATEGORY_SCORE_THRESHOLD", 0.35)
        )

    scores = result.get("category_scores") or {}
    if not scores:
        return False

    for v in scores.values():
        try:
            if float(v) >= threshold:
                return True
        except (TypeError, ValueError):
            continue
    return False


def categories_true(result: dict[str, Any]) -> list[str]:
    """Return category names that are True in the moderation `categories` map."""
    cats = result.get("categories") or {}
    if not isinstance(cats, dict):
        return []
    return [k for k, v in cats.items() if v is True]


def moderation_indicates_block(result: dict[str, Any]) -> bool:
    """
    Single gate for "block this text" using OpenAI moderation output.
    Aligns input and output paths: flagged OR high category score OR any category True.
    """
    if not result:
        return False
    if bool(result.get("flagged")):
        return True
    if should_block_from_category_scores(result):
        return True
    return bool(categories_true(result))


def is_openai_moderation_configured() -> bool:
    """True when an API key is present (moderation calls are intended)."""
    k = getattr(settings, "OPENAI_API_KEY", "") or ""
    return bool(k and k != "your-openai-api-key")


def moderation_indicates_block(result: dict[str, Any]) -> bool:
    """
    Single gate for "block this text" using OpenAI moderation output.
    Aligns input and output paths: flagged OR high category score OR any category True.
    """
    if not result:
        return False
    if bool(result.get("flagged")):
        return True
    if should_block_from_category_scores(result):
        return True
    return bool(categories_true(result))


def is_openai_moderation_configured() -> bool:
    """True when an API key is present (moderation calls are intended)."""
    k = getattr(settings, "OPENAI_API_KEY", "") or ""
    return bool(k and k != "your-openai-api-key")

