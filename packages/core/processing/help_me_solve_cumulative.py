"""Cumulative Help Me Solve It response enrichment for eval gold and production."""

from __future__ import annotations

from typing import Any


def _option_label(checkpoint: dict[str, Any] | None, choice: str | None) -> str | None:
    if not checkpoint or not choice:
        return None
    options = checkpoint.get("options") or []
    if not isinstance(options, list):
        return None
    for opt in options:
        if not isinstance(opt, dict):
            continue
        if str(opt.get("id", "")).upper() == str(choice).upper():
            return str(opt.get("label") or "").strip() or None
    return None


def _feedback_for_checkpoint(sections: list[dict[str, Any]], index: int) -> str | None:
    feedback_sections = [
        str(s.get("bodyMarkdown") or "").strip()
        for s in sections
        if isinstance(s, dict) and "feedback" in str(s.get("heading") or "").lower()
    ]
    if not feedback_sections:
        return None
    if index < len(feedback_sections):
        return feedback_sections[index] or None
    return feedback_sections[-1] or None


def _history_entry(
    checkpoint: dict[str, Any] | None,
    *,
    student_choice: str | None,
    feedback_markdown: str | None = None,
) -> dict[str, Any] | None:
    if not checkpoint or not isinstance(checkpoint, dict):
        return None
    number = int(checkpoint.get("number") or 0)
    if number <= 0:
        return None
    options = checkpoint.get("options") or []
    if not isinstance(options, list):
        options = []
    entry: dict[str, Any] = {
        "number": number,
        "prompt": str(checkpoint.get("prompt") or "").strip(),
        "options": [
            {
                "id": str(opt.get("id") or ""),
                "label": str(opt.get("label") or ""),
            }
            for opt in options
            if isinstance(opt, dict) and opt.get("id")
        ],
    }
    if student_choice:
        entry["studentChoice"] = str(student_choice).upper()
        label = _option_label(checkpoint, student_choice)
        if label:
            entry["selectedLabel"] = label
    if feedback_markdown:
        entry["feedbackMarkdown"] = feedback_markdown
    return entry


def enrich_help_me_solve_response(
    response: dict[str, Any],
    *,
    interaction_count: int,
    student_choice: str | None = None,
    prior_response: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Attach interactionCount and full checkpointHistory so eval gold is standalone.

    - interaction_count 1: history includes checkpoint 1 (from prior turn) + active checkpoint 2
    - interaction_count 2: history includes checkpoints 1 and 2 with both student choices
    """
    out = dict(response or {})
    sections = out.get("sections") if isinstance(out.get("sections"), list) else []
    history: list[dict[str, Any]] = []
    choice = (student_choice or "").strip().upper() or None

    if interaction_count >= 1 and prior_response:
        cp1 = prior_response.get("checkpoint")
        if isinstance(cp1, dict):
            cp1_choice = choice if interaction_count == 1 else "A"
            entry = _history_entry(
                cp1,
                student_choice=cp1_choice,
                feedback_markdown=_feedback_for_checkpoint(sections, 0),
            )
            if entry:
                history.append(entry)

    if interaction_count >= 2:
        prior_history = prior_response.get("checkpointHistory") if prior_response else None
        if isinstance(prior_history, list) and prior_history:
            history = [dict(h) for h in prior_history if isinstance(h, dict)]
            if history and choice:
                history[0].setdefault("studentChoice", "A")
                if not history[0].get("selectedLabel"):
                    history[0]["selectedLabel"] = _option_label(
                        prior_response.get("checkpoint") if prior_response else None,
                        history[0].get("studentChoice"),
                    )
        cp2_source = prior_response.get("checkpoint") if prior_response else None
        entry2 = _history_entry(
            cp2_source if isinstance(cp2_source, dict) else None,
            student_choice=choice or "A",
            feedback_markdown=_feedback_for_checkpoint(sections, 1),
        )
        if entry2 and entry2.get("number") == 2:
            if len(history) >= 2:
                history[1] = {**history[1], **{k: v for k, v in entry2.items() if v}}
            elif len(history) == 1:
                history.append(entry2)
            else:
                history.append(entry2)

    out["interactionCount"] = interaction_count
    if history:
        out["checkpointHistory"] = history
    return out
