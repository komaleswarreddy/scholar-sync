#!/usr/bin/env python3
"""
Static contract verification for NotebookLM-aligned mind map Studio behavior.

Checks frontend source files + api-client timeouts without a JS test runner.
Exit 0 = all checks pass; exit 1 = failures printed.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "apps" / "web" / "src"

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    if not ok:
        FAILURES.append(f"{name}: {detail}" if detail else name)


def read(rel: str) -> str:
    path = ROOT / rel.replace("/", "\\") if "\\" not in rel else ROOT / rel
    if not path.exists():
        FAILURES.append(f"Missing file: {path}")
        return ""
    return path.read_text(encoding="utf-8")


def main() -> int:
    ctx = read("apps/web/src/contexts/StudioGenerationContext.tsx")
    check(
        "StudioGenerationContext forces mind_map sources_only",
        "taskType === 'mind_map' ? 'sources_only'" in ctx
        and "taskType !== 'mind_map' && !explicitMode" in ctx,
    )
    check(
        "StudioGenerationContext skips instructions for mind_map",
        "taskType === 'mind_map' ? undefined : instructions" in ctx,
    )

    suite = read("apps/web/src/components/studio/StudioSuite.tsx")
    check(
        "StudioSuite handleMindMapGenerate uses sources_only only",
        "contextMode: 'sources_only'" in suite
        and "buildMindMapInstructions" not in suite,
    )
    check(
        "StudioSuite hint mentions mind map source-only",
        "chat does not affect the map" in suite.lower() or "does not affect the map" in suite,
    )

    toolbar = read("apps/web/src/components/chat/ChatStudioSelectionToolbar.tsx")
    check(
        "ChatStudioSelectionToolbar excludes mind_map",
        "mind_map" not in toolbar or "'mind_map'" not in toolbar,
        "mind_map still in selection toolbar ACTIONS",
    )
    check(
        "ChatStudioSelectionToolbar keeps quiz/flashcards/slide_deck",
        all(t in toolbar for t in ("quiz", "flashcards", "slide_deck")),
    )

    popover = read("apps/web/src/components/chat/NotebookChatSelectionPopover.tsx")
    check(
        "NotebookChatSelectionPopover filters out mind_map",
        'tool.type !== "mind_map"' in popover or "!== 'mind_map'" in popover,
    )

    api = read("apps/web/src/lib/api-client.ts")
    check("api-client exports STUDIO_GENERATION_TIMEOUT_MS", "STUDIO_GENERATION_TIMEOUT_MS" in api)
    mm_timeout = re.search(r"mind_map:\s*([\d_]+)", api)
    timeout_val = int(mm_timeout.group(1).replace("_", "")) if mm_timeout else 0
    check(
        "mind_map client timeout >= 120s",
        timeout_val >= 120_000,
        f"found {timeout_val}",
    )

    display = read("apps/web/src/components/studio/MindMapDisplay.tsx")
    check(
        "MindMapDisplay auto-expands level-1 on load",
        "buildLayoutTree.children.map" in display and "setExpandedNodes" in display,
    )

    service = read("packages/core/services/studio_service.py")
    check(
        "studio_service forces mind_map sources_only",
        'if task_type == "mind_map":' in service and 'mode = "sources_only"' in service,
    )
    check(
        "studio_service uses batch_generate_embeddings for broad retrieval",
        "batch_generate_embeddings" in service,
    )
    check(
        "studio_service parallel pinecone via to_thread",
        "asyncio.to_thread" in service and "_studio_pinecone_query_sync" in service,
    )

    if FAILURES:
        print("Mind map Studio contract verification FAILED:\n")
        for f in FAILURES:
            print(f"  - {f}")
        return 1

    print("Mind map Studio contract verification PASSED (frontend + backend static checks).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
