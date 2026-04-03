from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

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
    Aligns input and output paths:
    - always block on `flagged` or any category == True
    - optionally block on high category scores (production-gated to avoid false positives)
    """
    if not result:
        return False
    if bool(result.get("flagged")):
        return True
    if bool(getattr(settings, "MODERATION_BLOCK_ON_CATEGORY_SCORES", False)):
        if should_block_from_category_scores(result):
            return True
    return bool(categories_true(result))


_DEFAULT_HARD_SUBSTRINGS: tuple[str, ...] = (
    "sexual/minors",
    "sexual_minors",
    "illicit",
    "harassment/threatening",
    "harassment_threatening",
    "hate/threatening",
    "hate_threatening",
)


def _hard_category_substrings() -> tuple[str, ...]:
    raw = (getattr(settings, "MODERATION_OUTPUT_HARD_CATEGORY_SUBSTRINGS", "") or "").strip()
    if not raw:
        return _DEFAULT_HARD_SUBSTRINGS
    parts = tuple(x.strip().lower() for x in raw.split(",") if x.strip())
    return parts or _DEFAULT_HARD_SUBSTRINGS


def _norm_cat(name: str) -> str:
    return str(name or "").lower().replace("_", "/")


def _category_name_hard_blocks(name: str, hard_subs: Iterable[str]) -> bool:
    n = _norm_cat(name)
    for h in hard_subs:
        hs = h.lower().replace("_", "/")
        if hs in n:
            return True
    # Plain sexual content (non-minors) still block; educational medical bypass is for violence/self-harm FPs.
    if n == "sexual" or n.endswith("/sexual"):
        return True
    return False


def _float_score(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _max_score_for_keys(category_scores: Dict[str, Any], key_substrings: List[str]) -> float:
    m = 0.0
    for k, v in (category_scores or {}).items():
        kl = str(k).lower().replace("_", "/")
        if not any(sub in kl for sub in key_substrings):
            continue
        m = max(m, _float_score(v))
    return m


def educational_rag_output_heuristic(text: str) -> bool:
    """
    True when text plausibly looks like a sourced educational answer (not user self-harm disclosure).
    Used only for output moderation lenience.
    """
    t = (text or "").strip()
    if len(t) < 55:
        return False
    tl = t.lower()
    # Citations or structured answer markers
    if re.search(r"\[\d+\]", t):
        return True
    # Typical STEM / course vocabulary (reflex arc, hot pan, etc.)
    stem = re.compile(
        r"\b(reflex|neuron|spinal cord|brain|physiology|anatomy|biology|cellular|enzyme|"
        r"mitosis|photosynthesis|osmosis|dna|rna|muscle|tissue|organ|pathway|stimulus|"
        r"sensory|motor|nervous system|cortex|hormone|molecule|atom|velocity|force|reaction|"
        r"theorem|hypothesis|experiment|evidence|study|research|analysis|equation|pain receptors?)\b",
        re.I,
    )
    if stem.search(tl):
        return True
    # Academic framing + length
    if len(t) > 180 and re.search(
        r"\b(because|therefore|mechanism|process|occurs|function|structure|system)\b", tl
    ):
        return True
    return False


def _only_soft_violence_selfharm_categories(triggered: List[str], hard_subs: Iterable[str]) -> bool:
    """True if every True category is a bypassable violence/self-harm family (not hate/harassment/etc.)."""
    if not triggered:
        return False
    for name in triggered:
        n = _norm_cat(name)
        if _category_name_hard_blocks(name, hard_subs):
            return False
        if "graphic" in n or "instructions" in n:
            return False
        if any(x in n for x in ("threatening", "illicit", "sexual", "hate", "harassment")):
            return False
        soft = False
        if n == "violence" or (n.startswith("violence/") and "graphic" not in n):
            soft = True
        if "self-harm" in n:
            soft = True
        if not soft:
            return False
    return True


def moderation_indicates_block_output(result: dict[str, Any], text: str) -> bool:
    """
    Output-only moderation gate. Reduces false blocks on educational content that omni-moderation
    labels as violence/self-harm (e.g. burns, pain, reflex arcs) while keeping hard blocks for
    sexual, illicit, and threatening categories.
    """
    if not result:
        return False

    if bool(getattr(settings, "MODERATION_BLOCK_ON_CATEGORY_SCORES", False)):
        if should_block_from_category_scores(result):
            return True

    if not bool(getattr(settings, "MODERATION_OUTPUT_LENIENT", True)):
        return moderation_indicates_block(result)

    scores: Dict[str, Any] = dict(result.get("category_scores") or {})
    triggered = categories_true(result)
    flagged = bool(result.get("flagged"))
    hard_subs = _hard_category_substrings()

    for name in triggered:
        if _category_name_hard_blocks(name, hard_subs):
            return True

    instr_min = float(getattr(settings, "MODERATION_OUTPUT_INSTRUCTIONS_BLOCK_MIN", 0.22))
    graphic_min = float(getattr(settings, "MODERATION_OUTPUT_GRAPHIC_VIOLENCE_BLOCK_MIN", 0.22))
    if _max_score_for_keys(scores, ["self-harm/instructions", "self-harm_instructions"]) >= instr_min:
        return True
    if _max_score_for_keys(scores, ["violence/graphic", "violence_graphic"]) >= graphic_min:
        return True

    if not flagged and not triggered:
        return False

    # No scores from API — stay conservative
    if flagged and not scores:
        return True

    soft_cap = float(getattr(settings, "MODERATION_OUTPUT_SENSITIVE_ALLOW_UNDER_SCORE", 0.78))
    max_soft = 0.0
    for k, v in scores.items():
        kl = str(k).lower().replace("_", "/")
        if "illicit" in kl or "minor" in kl or "sexual" in kl:
            continue
        if "instructions" in kl:
            continue
        if "graphic" in kl:
            continue
        if "threatening" in kl:
            continue
        if "self-harm" in kl or kl == "violence" or kl.startswith("violence/"):
            max_soft = max(max_soft, _float_score(v))

    if max_soft >= soft_cap:
        return True

    if triggered and not _only_soft_violence_selfharm_categories(triggered, hard_subs):
        return True

    if educational_rag_output_heuristic(text):
        return False

    return True


def is_openai_moderation_configured() -> bool:
    """True when an API key is present (moderation calls are intended)."""
    k = getattr(settings, "OPENAI_API_KEY", "") or ""
    return bool(k and k != "your-openai-api-key")

