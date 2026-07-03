#!/usr/bin/env python3
"""Debug parse failures for agent 18 empty runs."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from langsmith import Client

from evals.agent_eval.coach_json_parse import _INVALID_ESCAPE_RE, json_dict_from_text, parse_coach_response

SESSIONS = {
    "v2": "e1d265a1-733f-46af-ac61-92faa26885ab",
    "v3": "5ab585ac-2e06-4c68-bf42-9d89af787869",
}


def debug_text(text: str) -> None:
    print("len", len(text))
    parsed = json_dict_from_text(text)
    print("json_dict_from_text", parsed is not None)
    if parsed:
        print("keys", list(parsed.keys())[:8])
        return

    raw = text.strip()
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*)", raw)
    if not m:
        print("no fence")
        return
    blob = m.group(1).split("```")[0].strip()
    print("blob len", len(blob))
    for label, candidate in (
        ("raw", blob),
        ("escaped", _INVALID_ESCAPE_RE.sub(r"\\\\", blob)),
    ):
        try:
            p = json.loads(candidate)
            print(f"{label} loads OK", isinstance(p, dict))
            return
        except json.JSONDecodeError as e:
            print(f"{label} err at {e.pos}: {e.msg}")
            start = max(0, e.pos - 40)
            print("context:", repr(candidate[start : e.pos + 40]))


def main() -> int:
    c = Client()
    for label, sid in SESSIONS.items():
        print("=" * 60, label)
        for r in c.list_runs(project_id=sid, is_root=True):
            if isinstance(r.outputs, dict) and r.outputs:
                continue
            for k in c.list_runs(trace_id=r.trace_id):
                if k.run_type == "llm":
                    text = str((k.outputs or {}).get("text") or "")
                    print("run", str(r.id)[:8], "text_len", len(text))
                    if text:
                        debug_text(text)
                    else:
                        print("EMPTY LLM text")
                    out = parse_coach_response(text)
                    print("parse_coach_response", bool(out))
                    print()
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
