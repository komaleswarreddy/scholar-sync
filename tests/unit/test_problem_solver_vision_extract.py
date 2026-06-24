"""Unit tests for problem-solver vision extraction helpers."""

from packages.core.processing.problem_solver_extraction import (
    assemble_problem_text,
    clean_problem_text_diagrams,
    detect_corruption,
    extract_mcq_options,
    filter_diagram_description,
    finalize_problem_text,
    is_meaningful_diagram_description,
    merge_problem_and_diagram,
    needs_vision_retry,
    pick_diagram_for_question,
    question_references_diagram,
    reconcile_text_layers,
    should_attach_diagram,
    strip_diagram_blocks,
    strip_options_from_diagram,
)


Q16_TEXT = (
    "Q16. Select the correct statements from the following: A. Atoms of all elements are composed "
    "of two fundamental particles. B. The mass of the electron is 9.10939 × 10⁻³¹ kg. "
    "Choose the correct answer from the options given below: a. B, C and E only"
)

Q16_BOGUS_DIAGRAM = (
    "[Diagram: The text presents a multiple-choice question regarding atomic theory and properties "
    "of particles. There are no numeric annotations, spatial layouts, or visual components such as "
    "arrows or connections, as the content is purely textual and does not include any diagrams or figures.]"
)


def test_detect_corruption_q29_broken():
    broken = (
        "Two blocks ( and ) with respectively masses kg and kg are joined by a massless thread. "
        "coefficient friction . acceleration of ... (1) (2) (3) (4)"
    )
    flags = detect_corruption(broken)
    assert "empty_parens" in flags or "missing_masses" in flags


def test_detect_corruption_clean():
    clean = "Two blocks (P and Q) with masses 2 kg and 1.5 kg. Find μ. (1) 0.33 (2) 0.67"
    assert not detect_corruption(clean)


def test_needs_vision_retry():
    assert needs_vision_retry("short", has_image=True)
    assert not needs_vision_retry("Two blocks (P and Q) with 2 kg", has_image=False)


def test_merge_problem_and_diagram_with_figure_reference():
    problem = "Q29. Two blocks shown in the figure below."
    merged = merge_problem_and_diagram(problem, "Cube S with blocks P and Q on pulley.")
    assert "[Diagram:" in merged
    assert merged.startswith("Q29.")


def test_phasor_derive_does_not_count_as_figure_reference():
    problem = (
        "Q30. Derive the current expression and construct the corresponding vector phasor diagram layout."
    )
    assert not question_references_diagram(problem)


def test_merge_skips_text_only_diagram():
    problem = Q16_TEXT
    merged = merge_problem_and_diagram(problem, Q16_BOGUS_DIAGRAM)
    assert "[Diagram:" not in merged


def test_filter_rejects_text_only_diagram():
    assert not is_meaningful_diagram_description(Q16_BOGUS_DIAGRAM)
    assert filter_diagram_description(Q16_BOGUS_DIAGRAM) == ""


def test_clean_problem_text_strips_bogus_q16():
    dirty = f"{Q16_TEXT}\n\n{Q16_BOGUS_DIAGRAM}"
    cleaned = clean_problem_text_diagrams(dirty, Q16_BOGUS_DIAGRAM)
    assert "[Diagram:" not in cleaned
    assert "Q16." in cleaned


def test_should_not_attach_text_only_q16():
    assert not should_attach_diagram(Q16_TEXT, Q16_BOGUS_DIAGRAM)


def test_should_attach_for_spatial_setup_without_figure_phrase():
    q36 = (
        "Q.36 A bead P sliding on a frictionless semi-circular string (A C B) and it is at point S "
        "at t = 0. Another bead Q is ejected from point A along the horizontal string A B."
    )
    diagram = (
        "The diagram shows a horizontal line AB with a semi-circular arc ACB below it. "
        "Bead Q is at point A with a horizontal arrow to the right. Bead P is at point S on the arc "
        "with a dashed radius at 45 degrees to the horizontal."
    )
    assert should_attach_diagram(q36, diagram)
    merged = merge_problem_and_diagram(q36, diagram)
    assert "[Diagram:" in merged


def test_pick_diagram_for_question_on_shared_page():
    q35 = "Q.35 To compare EMF of two cells using potentiometer the balancing lengths obtained are 200 cm and 150 cm."
    q36 = "Q.36 A bead P sliding on a frictionless semi-circular string (A C B) at point S."
    page_desc = (
        "[Diagram: A potentiometer setup with balancing lengths 200 cm and 150 cm labeled.]; "
        "[Diagram: A horizontal line AB with semi-circular arc ACB, bead P at S on the arc at 45 degrees, "
        "bead Q at A with horizontal velocity arrow.]"
    )
    picked_35 = pick_diagram_for_question(q35, page_desc)
    picked_36 = pick_diagram_for_question(q36, page_desc)
    assert "potentiometer" in picked_35.lower()
    assert "semi-circular" in picked_36.lower() or "bead" in picked_36.lower()


def test_strip_diagram_blocks():
    text = "Q1. Problem stem.\n\n[Diagram: some figure]"
    assert strip_diagram_blocks(text) == "Q1. Problem stem."


def test_reconcile_prefers_vision_when_corrupt():
    raw = "Two blocks ( and ) masses kg and kg"
    vis = "Two blocks (P and Q) with masses 2 kg and 1.5 kg"
    assert reconcile_text_layers(raw, vis) == vis


def test_reconcile_keeps_clean_text_layer():
    raw = "A long clean problem statement with all values 2 kg and 1.5 kg for blocks P and Q."
    vis = "shorter"
    assert reconcile_text_layers(raw, vis) == raw


def test_extract_mcq_options_jee_trailing():
    text = (
        "Q.36 then the relation between t P and t Q is\n"
        "1. t P > t Q\n"
        "2. t P = 1.25 t Q\n"
        "3. t P = t Q\n"
        "4. t P < t Q"
    )
    stem, options = extract_mcq_options(text)
    assert "relation between t P and t Q is" in stem
    assert "1. t P > t Q" in options
    assert "4. t P < t Q" in options


def test_assemble_order_diagram_before_options():
    stem = "Q.36 bead problem stem."
    diagram = "Semi-circular arc with beads P and Q."
    options = "1. t P > t Q\n2. t P = 1.25 t Q\n3. t P = t Q\n4. t P < t Q"
    merged = assemble_problem_text(stem, diagram, options)
    d_idx = merged.index("[Diagram:")
    o_idx = merged.index("1. t P > t Q")
    assert d_idx < o_idx
    assert merged.startswith("Q.36")


def test_q29_reorders_inline_options():
    stem = (
        "Q29. Two blocks shown in the figure below. Block P and Q remain stationary. "
        "The value of μ is ______. (1) 0.33 (2) 0.67 (3) 1 (4) 0.5"
    )
    diagram = "Cube S with blocks P and Q on pulley."
    merged = finalize_problem_text(stem, diagram, page_has_images=True)
    assert "[Diagram:" in merged
    assert merged.index("[Diagram:") < merged.index("(1) 0.33")
    assert "(4) 0.5" in merged


def test_strip_options_from_diagram():
    desc = (
        "The figure depicts a prism. The labels (1), (2), (3), and (4) are positioned near the bottom "
        "with values: (1) √3/4, (2) √3/2, (3) √5/4, and (4) √5/2."
    )
    cleaned, options = strip_options_from_diagram(desc)
    assert "(1) √3/4" in options or "(1)" in options
    assert "√5/2" in options or "√5" in options
    assert "labels (1)" not in cleaned.lower() or len(cleaned) < len(desc)


def test_q16_no_diagram_unchanged():
    merged = finalize_problem_text(Q16_TEXT, Q16_BOGUS_DIAGRAM)
    assert "[Diagram:" not in merged
    assert "a. B, C and E only" in merged


def test_split_questions_jee_page():
    from scripts.extract_problem_solver_questions import split_questions

    page = (
        "Q.35 To compare EMF of two cells using potentiometer the balancing lengths obtained are "
        "200 cm and 150 cm. The percentage error in the ratio of EMFs is _________\n"
        "1. 1.65\n2. 1.55\n3. 1.45\n4. 1.75\n\n"
        "Q.36 A bead P sliding on a frictionless semi-circular string (A C B) and it is at point S "
        "at t = 0. Let t P and t Q be the respective times taken by beads P and Q to reach point B, "
        "then the relation between t P and t Q is\n"
        "1. t P > t Q\n2. t P = 1.25 t Q\n3. t P = t Q\n4. t P < t Q"
    )
    parts = split_questions(page)
    assert len(parts) == 2
    q35_text = parts[0][1]
    q36_text = parts[1][1]
    assert "1.65" in q35_text or "1. 1.65" in q35_text
    assert "1. t P > t Q" in q36_text or "t P > t Q" in q36_text
