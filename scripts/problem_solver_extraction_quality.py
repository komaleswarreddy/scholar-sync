#!/usr/bin/env python3
"""Re-export problem-solver extraction quality helpers for scripts."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.core.processing.problem_solver_extraction import (  # noqa: F401
    clean_problem_text_diagrams,
    detect_corruption,
    filter_diagram_description,
    format_diagram_block,
    is_meaningful_diagram_description,
    merge_problem_and_diagram,
    needs_vision_retry,
    question_references_diagram,
    reconcile_text_layers,
    should_attach_diagram,
    strip_diagram_blocks,
)
