"""Unit tests for Help Me Solve It cumulative enrichment."""

from packages.core.processing.help_me_solve_cumulative import enrich_help_me_solve_response


def test_enrich_interaction_count_1_includes_checkpoint_history():
    prior = {
        "checkpoint": {
            "number": 1,
            "prompt": "Which idea?",
            "options": [
                {"id": "A", "label": "Use Ohm's law"},
                {"id": "B", "label": "Use power formula"},
            ],
        },
    }
    response = {
        "title": "Test",
        "sections": [
            {"heading": "Problem decode", "bodyMarkdown": "decode"},
            {"heading": "Feedback on your choice", "bodyMarkdown": "You picked A."},
        ],
        "checkpoint": {
            "number": 2,
            "prompt": "Next step?",
            "options": [{"id": "A", "label": "Substitute"}],
        },
    }
    out = enrich_help_me_solve_response(
        response,
        interaction_count=1,
        student_choice="A",
        prior_response=prior,
    )
    assert out["interactionCount"] == 1
    assert len(out["checkpointHistory"]) == 1
    assert out["checkpointHistory"][0]["studentChoice"] == "A"
    assert out["checkpointHistory"][0]["selectedLabel"] == "Use Ohm's law"
    assert out["checkpointHistory"][0]["feedbackMarkdown"] == "You picked A."


def test_enrich_interaction_count_2_includes_both_checkpoints():
    prior = {
        "checkpointHistory": [
            {
                "number": 1,
                "prompt": "Which idea?",
                "options": [{"id": "A", "label": "Correct idea"}],
                "studentChoice": "A",
                "selectedLabel": "Correct idea",
            }
        ],
        "checkpoint": {
            "number": 2,
            "prompt": "Next?",
            "options": [
                {"id": "A", "label": "Finish solve"},
                {"id": "B", "label": "Wrong path"},
            ],
        },
    }
    response = {
        "sections": [
            {"heading": "Feedback on checkpoint 1", "bodyMarkdown": "cp1 ok"},
            {"heading": "Feedback on checkpoint 2", "bodyMarkdown": "cp2 ok"},
            {"heading": "Solution walkthrough", "bodyMarkdown": "done"},
        ],
        "finalAnswer": "42",
    }
    out = enrich_help_me_solve_response(
        response,
        interaction_count=2,
        student_choice="A",
        prior_response=prior,
    )
    assert out["interactionCount"] == 2
    assert len(out["checkpointHistory"]) == 2
    assert out["checkpointHistory"][1]["studentChoice"] == "A"
    assert out["checkpointHistory"][1]["selectedLabel"] == "Finish solve"
