"""Unit tests for Problem Solver answer leak guard and session serialization."""

from packages.core.security.answer_leak_guard import answer_leak_guard, extract_final_answer


def test_extract_final_answer_from_expert_solution():
    assert extract_final_answer({"final_answer": "42 m/s"}) == "42 m/s"
    assert extract_final_answer({}) is None
    assert extract_final_answer(None) is None


def test_answer_leak_guard_scrubs_when_reveal_not_allowed():
    response = {
        "sections": [{"heading": "Hint", "bodyMarkdown": "The answer is 42 m/s"}],
        "finalAnswer": "42 m/s",
    }
    expert = {"final_answer": "42 m/s"}
    out = answer_leak_guard(response, expert_solution=expert, allow_reveal=False)
    assert "[answer hidden]" in out["sections"][0]["bodyMarkdown"]
    assert out["finalAnswer"] is None


def test_answer_leak_guard_allows_reveal_when_flagged():
    response = {
        "sections": [{"heading": "Solution", "bodyMarkdown": "42 m/s"}],
        "finalAnswer": "42 m/s",
    }
    expert = {"final_answer": "42 m/s"}
    out = answer_leak_guard(response, expert_solution=expert, allow_reveal=True)
    assert out["sections"][0]["bodyMarkdown"] == "42 m/s"
    assert out["finalAnswer"] == "42 m/s"


def test_session_to_public_strips_expert_solution():
    from packages.core.services.problem_solver_service import _session_to_public
    from packages.core.database.models.problem_solver import ProblemSolverSession
    import uuid

    session = ProblemSolverSession(
        tenant_id=uuid.uuid4(),
        user_id="user-1",
        notebook_id=uuid.uuid4(),
        problem_text="What is velocity?",
        problem_text_normalized="What is velocity?",
        expert_solution={"final_answer": "secret"},
        problem_dna={"subject": "Physics"},
    )
    session.id = uuid.uuid4()
    public = _session_to_public(session)
    assert "expert_solution" not in public
    assert public["problem_dna"]["subject"] == "Physics"
