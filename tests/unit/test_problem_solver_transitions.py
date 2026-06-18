"""Problem Solver state transition tests."""

from packages.core.services.problem_solver_service import VALID_TRANSITIONS


def test_valid_transitions_cover_happy_path():
    path = [
        "created",
        "dna_ready",
        "mode_selected",
        "responding",
        "completed",
    ]
    for i in range(len(path) - 1):
        current, nxt = path[i], path[i + 1]
        assert nxt in VALID_TRANSITIONS[current], f"{current} -> {nxt} should be allowed"


def test_help_me_solve_follow_up_state_allowed():
    assert "follow_up" in VALID_TRANSITIONS["responding"]
    assert "follow_up" in VALID_TRANSITIONS["follow_up"]
    assert "completed" in VALID_TRANSITIONS["follow_up"]
