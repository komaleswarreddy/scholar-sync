"""Load central chat policy from YAML for injection into RAG prompts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from config.settings import settings

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


def _default_policy_path() -> Path:
    return Path(__file__).resolve().parent.parent / "prompts" / "policies" / "chat_policy.default.yaml"


def load_chat_policy_dict() -> Dict[str, Any]:
    if not getattr(settings, "ENABLE_CHAT_POLICY_YAML", True):
        return {}
    path = getattr(settings, "CHAT_POLICY_YAML_PATH", None) or ""
    p = Path(path) if path else _default_policy_path()
    if yaml is None or not p.is_file():
        return {}
    try:
        raw = p.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _age_tier_bullets(policy: Dict[str, Any], tier: str) -> List[str]:
    raw = policy.get("age_appropriate_tiers")
    if not isinstance(raw, dict):
        return []
    key = (tier or "14-17").strip().lower()
    if key in {"9-12", "9-17"}:
        key = "14-17"
    items = raw.get(key)
    if not isinstance(items, list):
        return []
    out: List[str] = []
    for it in items:
        if isinstance(it, str) and it.strip():
            out.append(it.strip())
    return out


def build_chat_policy_block() -> str:
    """Render policy dict as a compact markdown section for the LLM."""
    d = load_chat_policy_dict()
    if not d:
        return ""

    lines: List[str] = []
    ts = (d.get("tone_summary") or "").strip()
    if ts:
        lines.append(f"**Tone:** {ts}")

    for key, label in (
        ("student_facing_rules", "Rules"),
        ("banned_output_patterns", "Avoid these patterns"),
        ("safety_reminders", "Safety"),
    ):
        items = d.get(key)
        if isinstance(items, list) and items:
            lines.append(f"\n**{label}:**")
            for it in items:
                if isinstance(it, str) and it.strip():
                    lines.append(f"- {it.strip()}")

    tier = str(getattr(settings, "STUDENT_AGE_TIER", "14-17") or "14-17").strip().lower()
    if tier in {"9-12", "9-17"}:
        tier = "14-17"
    age_lines = _age_tier_bullets(d, tier)
    if age_lines:
        lines.append("\n**Age-appropriate guidance (mandatory for this deployment):**")
        for it in age_lines:
            lines.append(f"- {it}")

    return "\n".join(lines).strip()
