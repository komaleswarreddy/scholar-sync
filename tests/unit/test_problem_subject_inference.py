"""Unit tests for problem subject inference."""

from packages.core.services.problem_subject_inference import (
    infer_problem_subject,
    normalize_dna_subject,
)

CAR_PROBLEM = (
    "A car accelerates uniformly from rest to 72 km/h in 10 seconds. "
    "Find (a) the acceleration in m/s² and (b) the distance covered in this time."
)

QUADRATIC = "Find the roots of the quadratic equation 2x² - 5x + 3 = 0 using the quadratic formula."


def test_car_problem_infers_physics_not_mathematics():
    result = infer_problem_subject(CAR_PROBLEM, ["mathematics", "science"])
    assert result["subject_key"] == "science"
    assert result["subject"] == "Physics"
    assert result["confidence"] in {"high", "medium"}
    assert result["science_branch"] == "physics"


def test_quadratic_infers_mathematics():
    result = infer_problem_subject(QUADRATIC, ["mathematics", "science"])
    assert result["subject_key"] == "mathematics"
    assert result["subject"] == "Mathematics"


def test_normalize_dna_corrects_math_mislabel_for_physics_problem():
    dna = {
        "subject": "Mathematics",
        "chapter": "Motion",
        "conceptTags": ["Acceleration", "Distance"],
    }
    scope = {"subject_keys": ["mathematics", "science"], "subject_labels": ["Mathematics", "Science"]}
    fixed = normalize_dna_subject(dna, CAR_PROBLEM, scope)
    assert fixed["subject"] == "Physics"
    assert fixed["subject_key"] == "science"
