"""Unit tests for Problem Solver checkpoint normalization."""

from packages.core.services.problem_subject_inference import infer_problem_subject
from packages.core.services.problem_solver_service import (
    _response_end_state,
    normalize_checkpoint,
    normalize_mode_response,
)


CAR_PROBLEM = (
    "A car accelerates uniformly from rest to 72 km/h in 10 seconds. "
    "Find (a) the acceleration in m/s² and (b) the distance covered in this time."
)


def test_normalize_checkpoint_fills_missing_options():
    out = normalize_checkpoint({"prompt": "Pick the first step", "number": 1})
    assert out is not None
    assert out["prompt"] == "Pick the first step"
    assert len(out["options"]) >= 2
    assert all("id" in o and "label" in o for o in out["options"])


def test_normalize_checkpoint_maps_choices_alias():
    out = normalize_checkpoint(
        {
            "question": "Which formula?",
            "choices": [
                {"key": "A", "text": "v = u + at"},
                {"key": "B", "text": "s = ut"},
            ],
        },
        checkpoint_number=2,
    )
    assert out is not None
    assert out["number"] == 2
    assert out["options"][0]["label"] == "v = u + at"


def test_normalize_mode_response_injects_checkpoint_for_help_me_solve_it():
    raw = {"title": "Guided", "sections": [{"heading": "Step 1", "bodyMarkdown": "hint"}]}
    out = normalize_mode_response(
        raw,
        solving_mode="HELP_ME_SOLVE_IT",
        interaction_count=0,
    )
    assert out["checkpoint"] is not None
    assert len(out["checkpoint"]["options"]) >= 2


def test_normalize_mode_response_removes_checkpoint_after_max_interactions():
    raw = {
        "title": "Done",
        "sections": [],
        "checkpoint": {"prompt": "extra", "options": []},
    }
    out = normalize_mode_response(
        raw,
        solving_mode="HELP_ME_SOLVE_IT",
        interaction_count=2,
    )
    assert out.get("checkpoint") is None


def test_response_end_state_follow_up_when_checkpoint_present():
    class _Session:
        solving_mode = "HELP_ME_SOLVE_IT"
        interaction_count = 0

    state = _response_end_state(
        _Session(),
        {"checkpoint": {"number": 1, "prompt": "Q", "options": [{"id": "A", "label": "x"}]}},
    )
    assert state == "follow_up"


def test_car_problem_infers_physics():
    inferred = infer_problem_subject(CAR_PROBLEM, allowed_subject_keys=["mathematics"])
    assert inferred["subject"] == "Physics"
    assert inferred["subject_key"] == "science"


def test_normalize_mode_response_maps_body_and_follow_up_aliases():
    raw = {
        "title": "Follow-up",
        "sections": [{"heading": "Next", "body": "Use $a = v/t$"}],
        "follow_up_buttons": [{"text": "Similar", "id": "GIVE_SIMILAR_PROBLEM"}],
    }
    out = normalize_mode_response(
        raw,
        solving_mode="EXPLAIN_FROM_BASICS",
        interaction_count=0,
    )
    assert out["sections"][0]["bodyMarkdown"] == "Use $a = v/t$"
    assert out["followUpButtons"][0]["action"] == "GIVE_SIMILAR_PROBLEM"
    assert out["followUpButtons"][0]["label"] == "Similar"
