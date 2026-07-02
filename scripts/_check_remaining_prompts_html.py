#!/usr/bin/env python3
"""One-off check: can we extract A/B/C from reamingin promts.html for 7 agents?"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "Reference dataset" / "reamingin promts.html"

TARGETS = {"21", "22", "23", "24", "25", "32", "33"}
SNO_TO_ID = {
    "21": "help_me_solve_it",
    "22": "problem_solver_followup",
    "23": "tutor_notebook_bootstrap",
    "24": "tutor_follow_up_questions",
    "25": "source_question_extraction",
    "32": "image_ocr",
    "33": "diagram_label_ocr",
}


def clean(x) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    s = str(x).strip()
    return "" if s.lower() == "nan" else s


def main() -> int:
    if not HTML_PATH.is_file():
        print(f"NOT FOUND: {HTML_PATH}")
        return 1

    t = pd.read_html(HTML_PATH, encoding="utf-8")[0]
    t2 = t.iloc[1:].copy()
    t2.columns = ["rownum", "sno", "agent", "va", "vb", "vc", "col_g", "col_h"]

    found: set[str] = set()
    all_ok = True
    print("=== TARGET AGENTS in reamingin promts.html ===")
    for _, r in t2.iterrows():
        sno = clean(r["sno"]).strip()
        if sno not in TARGETS:
            continue
        found.add(sno)
        agent = clean(r["agent"])
        va, vb, vc = clean(r["va"]), clean(r["vb"]), clean(r["vc"])
        ok = bool(va and vb and vc)
        all_ok = all_ok and ok
        print(f"\nsno={sno} -> {SNO_TO_ID[sno]}")
        print(f"  name: {agent}")
        print(f"  A={len(va)} | B={len(vb)} | C={len(vc)} | complete={ok}")
        print(f"  A preview: {va[:100].replace(chr(10), ' ')}...")
        if vb:
            print(f"  B preview: {vb[:100].replace(chr(10), ' ')}...")
        if vc:
            print(f"  C preview: {vc[:100].replace(chr(10), ' ')}...")
        if not ok:
            missing = [k for k, v in [("A", va), ("B", vb), ("C", vc)] if not v]
            print(f"  MISSING: {missing}")

    missing_snos = TARGETS - found
    print("\n=== SUMMARY ===")
    print("Found snos:", sorted(found, key=int))
    print("Missing snos:", sorted(missing_snos, key=int) if missing_snos else "none")
    print("All found have A+B+C:", all_ok)
    extractable = all_ok and not missing_snos
    print("EXTRACTABLE:", extractable)
    return 0 if extractable else 2


if __name__ == "__main__":
    raise SystemExit(main())
