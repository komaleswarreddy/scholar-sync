#!/usr/bin/env python3
"""
Static contract verification for exploratory notebook chat grounding.

Ensures frontend defaults and backend guards that prevent NCERT global merge
from polluting selected-source retrieval in exploratory mode.
Exit 0 = pass; exit 1 = failures printed.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if not ok:
        FAILURES.append(f"{name}: {detail}" if detail else name)


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        FAILURES.append(f"Missing file: {path}")
        return ""
    return path.read_text(encoding="utf-8")


def main() -> int:
    chat_ui = read("apps/web/src/components/chat/ChatInterface.tsx")
    check(
        "ChatInterface defaults includeNcertGlobal to false for exploratory",
        "useState(false)" in chat_ui
        and "includeNcertGlobal" in chat_ui
        and "isTutorMode ? true : includeNcertGlobal" in chat_ui,
    )
    check(
        "ChatInterface keeps tutor mode NCERT always on",
        "effectiveIncludeNcertGlobal = isTutorMode ? true : includeNcertGlobal" in chat_ui,
    )

    graph = read("packages/core/langgraph/chat_graph.py")
    check(
        "chat_graph defines _ncert_global_merge_allowed",
        "def _ncert_global_merge_allowed" in graph,
    )
    check(
        "retrieval node uses effective NCERT merge flag",
        "include_g = _ncert_global_merge_allowed(state)" in graph,
    )
    check(
        "context select filters matches to active_source_ids",
        "_filter_matches_to_active_sources" in graph
        and "matches = _filter_matches_to_active_sources(matches, active)" in graph,
    )
    check(
        "document summary exemption checks original message",
        "def _is_document_summary_query_from_state" in graph
        and 'state["context_grounding_passed"] = True' in graph,
    )
    check(
        "two-stage grounding uses document summary from state",
        "whole_file_summary=doc_summary" in graph
        and "doc_summary = _is_document_summary_query_from_state(state)" in graph,
    )
    check(
        "document summary patterns include meta source queries",
        '"sources about"' in graph and '"what are those"' in graph,
    )

    unit = read("tests/unit/test_exploratory_chat_grounding.py")
    check(
        "unit tests cover NCERT merge suppression and context filter",
        "test_ncert_merge_blocked_when_uploads_selected_without_scope" in unit
        and "test_context_select_filters_out_ncert_chunks_when_active_sources_set" in unit,
    )

    if FAILURES:
        print("Exploratory chat contract verification FAILED:\n")
        for f in FAILURES:
            print(f"  - {f}")
        return 1

    print("Exploratory chat contract verification PASSED (frontend + backend static checks).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
