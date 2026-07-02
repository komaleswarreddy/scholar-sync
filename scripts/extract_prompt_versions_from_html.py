#!/usr/bin/env python3
"""Extract Version A/B/C prompts from Final Prompt Versions.html -> prompt_versions/.

The HTML cells are the FULL production .j2 templates (with {{ vars }}/{% %}), so we
store each version as v{N}_system.txt verbatim and pair it with a short v{N}_user.j2
nudge. render_prompts() Jinja-renders the system with dataset inputs at run time.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "Remaining_python_Evals" / "remaining_system_prompts" / "Final Prompt Versions.html"
OUT_ROOT = ROOT / "evals" / "agent_eval" / "prompt_versions"

# S.no in the sheet -> agent_id (only the 9 runnable text agents)
SNO_TO_AGENT = {
    "17": "problem_dna_analyzer",
    "18": "explain_from_basics",
    "19": "show_best_approach",
    "20": "show_missing_idea",
    "26": "document_sketch",
    "27": "ncert_document_sketch",
    "28": "chunk_contextualization",
    "29": "whole_file_map_summarizer",
    "30": "whole_file_reduce",
}

USER_NUDGE = (
    "Produce the output now, following the instructions above. "
    "Return only the required format (JSON only if the instructions specify JSON), "
    "with no extra commentary.\n"
)


def _clean(text: str) -> str:
    if text is None:
        return ""
    s = str(text).strip()
    if s.lower() == "nan":
        return ""
    # Normalize the Unicode replacement char that can appear for em dashes etc.
    return s


def main() -> int:
    if not HTML_PATH.is_file():
        raise SystemExit(f"HTML not found: {HTML_PATH}")
    t = pd.read_html(HTML_PATH, encoding="utf-8")[0]
    t = t.iloc[2:].copy()
    t.columns = ["idx", "sno", "agent", "va", "vb", "vc", "x"]

    written = []
    for _, r in t.iterrows():
        sno = str(r["sno"]).strip()
        agent_id = SNO_TO_AGENT.get(sno)
        if not agent_id:
            continue
        versions = {"v1": _clean(r["va"]), "v2": _clean(r["vb"]), "v3": _clean(r["vc"])}
        if not all(versions.values()):
            raise SystemExit(f"{agent_id} (sno {sno}) missing one of A/B/C")
        agent_dir = OUT_ROOT / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        for ver, system_text in versions.items():
            (agent_dir / f"{ver}_system.txt").write_text(system_text + "\n", encoding="utf-8")
            (agent_dir / f"{ver}_user.j2").write_text(USER_NUDGE, encoding="utf-8")
        written.append(f"{agent_id} (sno {sno}): {len(versions['v1'])}/{len(versions['v2'])}/{len(versions['v3'])} chars")

    print("Wrote prompt versions for %d agents:" % len(written))
    for w in written:
        print("  -", w)
    if len(written) != len(SNO_TO_AGENT):
        print("WARNING: expected", len(SNO_TO_AGENT), "agents", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
