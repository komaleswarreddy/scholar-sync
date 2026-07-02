"""Ensure Studio system prompt stays aligned with the canonical shared role partial."""

from packages.core.prompts.loader import get_loader


def _normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in (text or "").strip().splitlines())


def test_studio_system_prompt_matches_shared_role_partial():
    """CI guard: system_educational_json_markdown.j2 must render the same role block as the partial."""
    loader = get_loader()

    canonical = loader.load("studio/_shared_educational_role.j2")
    rendered_system = loader.load("studio/system_educational_json_markdown.j2")

    assert _normalize(rendered_system) == _normalize(canonical), (
        "studio/system_educational_json_markdown.j2 drifted from "
        "studio/_shared_educational_role.j2 — update the include or canonical partial."
    )
