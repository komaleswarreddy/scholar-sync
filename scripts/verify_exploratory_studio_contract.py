#!/usr/bin/env python3
"""Static checks: exploratory Studio disabled without uploaded sources."""

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
    suite = read("apps/web/src/components/studio/StudioSuite.tsx")
    check(
        "StudioSuite gates exploratory on uploaded sources",
        "notebookModeRequiresUploadedSources" in suite
        and "studioToolsEnabled" in suite
        and "EXPLORATORY_STUDIO_NO_SOURCES_MESSAGE" in suite,
    )
    check(
        "StudioSuite shows Select sources when disabled",
        "'Select sources'" in suite or '"Select sources"' in suite,
    )

    ctx = read("apps/web/src/contexts/StudioGenerationContext.tsx")
    check(
        "StudioGenerationContext blocks selection_only without sources in exploratory",
        "EXPLORATORY_STUDIO_SELECTION_BLOCKED_MESSAGE" in ctx
        and "requiresUploadedSources" in ctx,
    )

    popover = read("apps/web/src/components/chat/NotebookChatSelectionPopover.tsx")
    check(
        "NotebookChatSelectionPopover blocks studio without sources",
        "exploratoryStudioBlocked" in popover,
    )

    service = read("packages/core/services/studio_service.py")
    check(
        "studio_service rejects non-selection modes without sources",
        'mode != "selection_only" and n_sources < 1' in service,
    )

    unit = read("tests/unit/test_studio_exploratory_sources.py")
    check("unit test for empty sources_only", "test_studio_generate_rejects_sources_only_without_ids" in unit)

    if FAILURES:
        print("Exploratory Studio contract verification FAILED:\n")
        for f in FAILURES:
            print(f"  - {f}")
        return 1

    print("Exploratory Studio contract verification PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
